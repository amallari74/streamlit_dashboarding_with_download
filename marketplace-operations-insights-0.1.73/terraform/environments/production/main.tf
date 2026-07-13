terraform {
  required_version = "~> 1.2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.9.0"
    }
  }

  backend "s3" {
    bucket               = "pax8-tf-state-production"
    key                  = "aws/production.marketplace-operations-insights.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "env"
    encrypt              = true
    dynamodb_table       = "terraform-state-locking"
  }
}

provider "aws" {
  region = "us-east-1"

  assume_role {
    role_arn = "arn:aws:iam::778379446536:role/OrganizationAccountAccessRole"
  }
}

locals {
  service_name = "marketplace-operations-insights"
  namespace    = "data-platform"
  account_name = "production"
  account_id   = "778379446536"
}

#module "microservice" {
#  source = "git::git@github.com:pax8/terraform-modules//microservice_base"
#
#  account_name = local.account_name
#  service_name = local.service_name
#  namespace    = local.namespace
#
#  service_account_iam_role = false
#}

module "sm" {
  source       = "git::git@github.com:pax8/terraform-modules//secrets_manager"
  service_name = local.service_name
  account_name = local.account_name
  account_id   = local.account_id
  namespace    = local.namespace
}


data "aws_iam_policy_document" "policy" {
  statement {
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "arn:aws:s3:::pax8-p8p-production/invoices",
      "arn:aws:s3:::pax8-p8p-production/test_invoices",
      "arn:aws:s3:::pax8-p8p-production/invoices/*",
      "arn:aws:s3:::pax8-p8p-production/test_invoices/*"
    ]
  }
}


resource "aws_iam_policy" "policy" {
  name        = "s3_read_pax8_p8p_production_invoices"
  description = "Policy used by marketplace-operations-insights"
  policy      = data.aws_iam_policy_document.policy.json
}

resource "aws_iam_role_policy_attachment" "attach" {
  role       = module.sm.service_account_role_name
  policy_arn = aws_iam_policy.policy.arn
}
