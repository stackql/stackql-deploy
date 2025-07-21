---
id: index
title: Welcome
hide_title: true
hide_table_of_contents: true
# keywords: []
description: ''
# image: ''
# slug: ''
custom_edit_url: null
tags: []
draft: false
unlisted: false
---

![StackQL Deploy](/img/stackql-deploy-featured-image.png)

## Model Driven, Declarative, State File<i>-less</i>, Multi-Cloud IaC

<!-- <img src="/img/stackql-deploy.gif" alt="StackQL Deploy" title="StackQL Deploy" class="vhsImage"/> -->

__`stackql-deploy`__ is a multi-cloud resource provisioning framework using __`stackql`__. It is inspired by dbt (data build tool), which manages data transformation workflows in analytics engineering by treating SQL scripts as models that can be built, tested, and materialized incrementally. With StackQL, you can create a similar framework for cloud and SaaS provisioning. The goal is to treat cloud stacks as models that can be deployed, tested, updated, and de-provisioned, enabling developers to deploy complex, dependent infrastructure components in a reliable and repeatable manner. 

### Features

- Dynamic state determination (eliminating the need for state files)
- Pre-flight and post-deploy assurance tests for resources
- Simple flow control with rollback capabilities
- Single code base for multiple target environments
- SQL-based definitions for resources and tests

