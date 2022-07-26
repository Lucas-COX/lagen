variable "aws_region" {
    description = "AWS Region for the created resources"

    type = string
    default = {{ aws_region }}
}
