variable "tenancy_ocid" {
  description = "OCID of the OCI tenancy"
  type        = string
}

variable "user_ocid" {
  description = "OCID of the OCI user used by Terraform (API key auth)"
  type        = string
}

variable "fingerprint" {
  description = "Fingerprint of the API signing key for the OCI user"
  type        = string
}

variable "private_key_path" {
  description = "Path to the private API signing key (PEM)"
  type        = string
}

variable "compartment_ocid" {
  description = "OCID of the parent compartment under which the cic-poc compartment is created (typically the tenancy root compartment)"
  type        = string
}

variable "oci_region" {
  description = "OCI region. Choose one with available Always Free Ampere A1 capacity (see oci-infra-sketch.md chapter 5)."
  type        = string
  default     = "eu-frankfurt-1"
}

variable "ssh_public_key" {
  description = "SSH public key authorized on all PoC instances (PoC simplification: same key everywhere)"
  type        = string
}
