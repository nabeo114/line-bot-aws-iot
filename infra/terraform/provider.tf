locals {
  provider_default_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
    },
    var.default_tags
  )
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.provider_default_tags
  }
}
