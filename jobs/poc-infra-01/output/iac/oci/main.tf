terraform {
  required_providers {
    oci = {
      source  = "hashicorp/oci"
      version = "~> 6.0"
    }
  }
}

provider "oci" {
  region           = var.oci_region
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
}

# --- Compartment -----------------------------------------------------------

resource "oci_identity_compartment" "cic_poc" {
  compartment_id = var.compartment_ocid
  name           = "cic-poc"
  description    = "CIC PoC demo infrastructure (Milestone 0)"
  enable_delete  = true
}

# --- Network -----------------------------------------------------------------

resource "oci_core_vcn" "cic_poc_vcn" {
  compartment_id = oci_identity_compartment.cic_poc.id
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "cic-poc-vcn"
  dns_label      = "cicpoc"
}

resource "oci_core_internet_gateway" "cic_poc_igw" {
  compartment_id = oci_identity_compartment.cic_poc.id
  vcn_id         = oci_core_vcn.cic_poc_vcn.id
  display_name   = "cic-poc-igw"
  enabled        = true
}

resource "oci_core_route_table" "cic_poc_rt" {
  compartment_id = oci_identity_compartment.cic_poc.id
  vcn_id         = oci_core_vcn.cic_poc_vcn.id
  display_name   = "cic-poc-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.cic_poc_igw.id
  }
}

# Security list rules per oci-infra-sketch.md chapter 2.
# This list's canonical hash is the security_rules_hash referenced by
# poc-drift-detection-01 (system-plan.md 2.2) — manual edits to these
# rules during the 8.2 demo phase are intentional drift triggers.
resource "oci_core_security_list" "cic_poc_sl" {
  compartment_id = oci_identity_compartment.cic_poc.id
  vcn_id         = oci_core_vcn.cic_poc_vcn.id
  display_name   = "cic-poc-sl"

  # SSH from anywhere -> Bastion
  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"

    tcp_options {
      min = 22
      max = 22
    }
  }

  # SSH from within the VCN -> internal VMs (Bastion -> Vault/Relay/Demo target)
  ingress_security_rules {
    protocol = "6"
    source   = "10.0.0.0/16"

    tcp_options {
      min = 22
      max = 22
    }
  }

  # Vault API (Relay -> Vault)
  ingress_security_rules {
    protocol = "6"
    source   = "10.0.0.0/16"

    tcp_options {
      min = 8200
      max = 8200
    }
  }

  # Relay HTTP API
  ingress_security_rules {
    protocol = "6"
    source   = "10.0.0.0/16"

    tcp_options {
      min = 8080
      max = 8080
    }
  }

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

resource "oci_core_subnet" "cic_poc_subnet" {
  compartment_id             = oci_identity_compartment.cic_poc.id
  vcn_id                     = oci_core_vcn.cic_poc_vcn.id
  cidr_block                 = "10.0.1.0/24"
  display_name               = "cic-poc-subnet"
  dns_label                  = "cicpocsub"
  route_table_id             = oci_core_route_table.cic_poc_rt.id
  security_list_ids          = [oci_core_security_list.cic_poc_sl.id]
  prohibit_public_ip_on_vnic = false
}

# --- Image / AD lookups ------------------------------------------------------

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

locals {
  ad = data.oci_identity_availability_domains.ads.availability_domains[0].name
}

# Bastion: AMD Always Free shape (E2.1.Micro)
data "oci_core_images" "ubuntu_amd64" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                     = "VM.Standard.E2.1.Micro"
  sort_by                   = "TIMECREATED"
  sort_order                = "DESC"
}

# Vault/Relay/Demo target: Ampere A1 (ARM64)
data "oci_core_images" "ubuntu_arm64" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                     = "VM.Standard.A1.Flex"
  sort_by                   = "TIMECREATED"
  sort_order                = "DESC"
}

# --- Compute instances --------------------------------------------------------

resource "oci_core_instance" "bastion" {
  compartment_id      = oci_identity_compartment.cic_poc.id
  availability_domain = local.ad
  display_name        = "cic-poc-bastion"
  shape                = "VM.Standard.E2.1.Micro"

  create_vnic_details {
    subnet_id        = oci_core_subnet.cic_poc_subnet.id
    assign_public_ip = true
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_amd64.images[0].id
    boot_volume_size_in_gbs = 47
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }
}

resource "oci_core_instance" "vault" {
  compartment_id      = oci_identity_compartment.cic_poc.id
  availability_domain = local.ad
  display_name        = "cic-poc-vault"
  shape                = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 1
    memory_in_gbs = 6
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.cic_poc_subnet.id
    assign_public_ip = false
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_arm64.images[0].id
    boot_volume_size_in_gbs = 47
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }
}

resource "oci_core_instance" "relay" {
  compartment_id      = oci_identity_compartment.cic_poc.id
  availability_domain = local.ad
  display_name        = "cic-poc-relay"
  shape                = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 1
    memory_in_gbs = 6
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.cic_poc_subnet.id
    assign_public_ip = false
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_arm64.images[0].id
    boot_volume_size_in_gbs = 47
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }
}

# Demo target: Terraform create/destroy target for the 8.1/8.3 demo phases
# (poc-observer-plugin-01 / poc-drift-detection-01 build on this instance's OCID).
resource "oci_core_instance" "demo_target" {
  compartment_id      = oci_identity_compartment.cic_poc.id
  availability_domain = local.ad
  display_name        = "cic-poc-demo-target"
  shape                = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 2
    memory_in_gbs = 12
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.cic_poc_subnet.id
    assign_public_ip = false
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_arm64.images[0].id
    boot_volume_size_in_gbs = 47
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }
}
