terraform {
  required_version = "~> 1.2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.9.0"
    }
  }

  backend "s3" {
    bucket               = "pax8-terraform-state"
    key                  = "aws/pax8.marketplace-operations-insights.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "env"
    encrypt              = true
    dynamodb_table       = "terraform-state-locking"
  }
}

provider "aws" {
  region = "us-east-1"
}

locals {
  service_name = "marketplace-operations-insights"
}

module "ecr-repo" {
  source    = "git::git@github.com:pax8/terraform-modules//ecr"
  repo_name = local.service_name
}
