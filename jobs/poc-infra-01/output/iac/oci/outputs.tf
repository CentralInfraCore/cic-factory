output "compartment_id" {
  description = "OCID of the cic-poc compartment"
  value       = oci_identity_compartment.cic_poc.id
}

output "vcn_id" {
  value = oci_core_vcn.cic_poc_vcn.id
}

output "subnet_id" {
  value = oci_core_subnet.cic_poc_subnet.id
}

output "bastion_id" {
  value = oci_core_instance.bastion.id
}

output "bastion_public_ip" {
  value = oci_core_instance.bastion.public_ip
}

output "vault_id" {
  value = oci_core_instance.vault.id
}

output "vault_private_ip" {
  value = oci_core_instance.vault.private_ip
}

output "relay_id" {
  value = oci_core_instance.relay.id
}

output "relay_private_ip" {
  value = oci_core_instance.relay.private_ip
}

# Referenced by poc-observer-plugin-01's snapshot step (cic.iac.snapshot@1.0,
# system-plan.md 2.2) as the instance_ocid for the first actual_state.json.
output "demo_target_id" {
  description = "OCID of the demo_target instance"
  value       = oci_core_instance.demo_target.id
}

output "demo_target_private_ip" {
  value = oci_core_instance.demo_target.private_ip
}
