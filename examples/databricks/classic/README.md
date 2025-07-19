# `stackql-deploy` example project for `databricks`

This exercise is to bootstrap a databricks / aws tenancy using `stackql-deploy`.  It is an important use case for platform bootstrap and we are excited to perform it with the `stackql` toolchain.  We hope you enjoy and find this valuable.  Please drop us a note with your forthright opinion on this and check out our issues on github.

## A word of caution

Please take the greatest care in performing this exercise; it will incur expenses, as it involves creating (and destroying) resources which cost money. Please be aware that you **must** cancel your databricks subscription after completing this exercise, otherwise you will incur ongoing expenses.  That is, do **not** skip the section [Cancel databricks subscription](#cancel-databricks-subsription).  We strongly advise that you verify all resources are destroyed at the conclusion of this exercise.  Web pages and certain behaviours may change, so please be thorough in your verification.  We will keep this page up-to-date on a best effort basis only.  It is very much a case of owner onus applies.

## Manual Setup

Dependencies:

- aws Account Created.
- Required clickops to set up databricks on aws:
    - Turn on aws Marketplace `databricks` offering, using [the aws manage subscriptions page](https://console.aws.amazon.com/marketplace/home#/subscriptions), per Figure S1.
    - Follow the suggested setup flow as directed, from this page.  These clickops steps are necessary at this time for initial account setup.  The way I followed this, it created a workspace for me at setup, per Figure S3.  We shall not use this one and rather, later on we shall dispose of it; because we do not trust auto-created resources out of hand.  In the process of creating the databricks subscription, a second aws account is created.
    - Copy the databricks account id from basically any web page in the databricks console.  This is done by clicking on the user icon at the top RHS and then the UI provides a copy shortcut, per Fugure U1.  Save this locally for later use, expanded below.
    - We need the aws account id that was created for the databricks subscription.  It is not exactly heralded by the web pages, nor is it actively hidden.  It can be captured in a couple of places, including the databricks storage account creatted in the subscription flow, per Figure XA1.  copy and save this locally for later use, expanded below. 
    - Create a service principal to use as a "CICD agent", using the page shown in Figure S4.
    - Grant the CICD agent account admin role, using the page shown in Figure S5.
    - Create a secret for the CICD agent, using the page shown in Figure S6.  At the time you create this, you will need to safely store the client secret and client id, as prompted by the web page.  These will be used below.
- Setup your virtual environment, from the root  of this repository `cicd/setup/setup-env.sh`.

Now, is is convenient to use environment variables for context.  Note that for our example, there is only one aws account apropos, however this is not always the case for an active professional, so while `DATABRICKS_AWS_ACCOUNT_ID` is the same as `AWS_ACCOUNT_ID` here, it need not always be the case. Create a file in the path `examples/databricks/all-purpose-cluster/sec/env.sh` (relative to the root of this repository) with contents of the form:

```bash
#!/usr/bin/env bash

export AWS_REGION='us-east-1' # or wherever you want
export AWS_ACCOUNT_ID='<your aws account ID>'
export DATABRICKS_ACCOUNT_ID='<your databricks account ID>'
export DATABRICKS_AWS_ACCOUNT_ID='<your databricks aws account ID>'

# These need to be created by clickops under [the account level user managment page](https://accounts.cloud.databricks.com/user-management).
export DATABRICKS_CLIENT_ID='<your clickops created CICD agent client id>'
export DATABRICKS_CLIENT_SECRET='<your clickops created CICD agent client secret>'

## These can be skipped if you run on [aws cloud shell](https://docs.aws.amazon.com/cloudshell/latest/userguide/welcome.html).
export AWS_SECRET_ACCESS_KEY='<your aws secret per aws cli>'
export AWS_ACCESS_KEY_ID='<your aws access key id per aws cli>'

```

## Optional step: sanity checks with stackql

Now, let us do some sanity checks and housekeeping with `stackql`.  This is purely optional.  From the root of this repository: 

```
source examples/databricks/all-purpose-cluster/convenience.sh
stackql shell
```

This will start a `stackql` interactive shell.  Here are some commands you can run (I will not place output here, that will be shared in a corresponding video):


```sql
registry pull databricks_account v24.12.00279;
registry pull databricks_workspace v24.12.00279;

-- This will fail if accounts, subscription, or credentials are in error.
select account_id FROM databricks_account.provisioning.credentials WHERE account_id = '<your databricks account id>';
select account_id, workspace_name, workspace_id, workspace_status from databricks_account.provisioning.workspaces where account_id = '<your databricks account id>';
```

For extra credit, you can (asynchronously) delete the unnecessary workspace with `delete from databricks_account.provisioning.workspaces where account_id = '<your databricks account id>' and workspace_id = '<workspace id>';`, where you obtain the workspace id from the above query.  I have noted that due to some reponse caching it takes a while to disappear from select queries (much longer than disappearance from the web page), and you may want to bounce the `stackql` session to hurry things along.  This is not happening on the `stackql` side, but session bouncing forces a token refresh which can help cache busting. 

## Lifecycle management

Time to get down to business.  From the root of this repository:

```bash
python3 -m venv myenv
source examples/databricks/all-purpose-cluster/convenience.sh
source venv/bin/activate
pip install stackql-deploy
```

> alternatively set the `AWS_REGION`, `AWS_ACCOUNT_ID`, `DATABRICKS_ACCOUNT_ID`, `DATABRICKS_AWS_ACCOUNT_ID` along with provider credentials `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`

Then, do a dry run (good for catching **some** environmental issues):

```bash
stackql-deploy build \
examples/databricks/all-purpose-cluster dev \
-e AWS_REGION=${AWS_REGION} \
-e AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID} \
-e DATABRICKS_ACCOUNT_ID=${DATABRICKS_ACCOUNT_ID} \
-e DATABRICKS_AWS_ACCOUNT_ID=${DATABRICKS_AWS_ACCOUNT_ID} \
--dry-run
```

You will see a verbose rendition of what `stackql-deploy` intends to do.


Now, let use do it for real:

```bash
stackql-deploy build \
examples/databricks/all-purpose-cluster dev \
-e AWS_REGION=${AWS_REGION} \
-e AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID} \
-e DATABRICKS_ACCOUNT_ID=${DATABRICKS_ACCOUNT_ID} \
-e DATABRICKS_AWS_ACCOUNT_ID=${DATABRICKS_AWS_ACCOUNT_ID} \
--show-queries
```

The output is quite verbose, concludes in:

```
2025-02-08 12:51:25,914 - stackql-deploy - INFO - 📤 set [databricks_workspace_id] to [482604062392118] in exports
2025-02-08 12:51:25,915 - stackql-deploy - INFO - ✅ successfully deployed databricks_workspace
2025-02-08 12:51:25,915 - stackql-deploy - INFO - deployment completed in 0:04:09.603631
🚀 build complete
```

Success!!!

We can also use `stackql-deploy` to assess if our infra is shipshape:

```bash
stackql-deploy test \
examples/databricks/all-purpose-cluster dev \
-e AWS_REGION=${AWS_REGION} \
-e AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID} \
-e DATABRICKS_ACCOUNT_ID=${DATABRICKS_ACCOUNT_ID} \
-e DATABRICKS_AWS_ACCOUNT_ID=${DATABRICKS_AWS_ACCOUNT_ID} \
--show-queries
```

Again, the output is quite verbose, concludes in:

```
2025-02-08 13:15:45,821 - stackql-deploy - INFO - 📤 set [databricks_workspace_id] to [482604062392118] in exports
2025-02-08 13:15:45,821 - stackql-deploy - INFO - ✅ test passed for databricks_workspace
2025-02-08 13:15:45,821 - stackql-deploy - INFO - deployment completed in 0:02:30.255860
🔍 tests complete (dry run: False)
```

Success!!!

Now, let us teardown our `stackql-deploy` managed infra:

```bash
stackql-deploy teardown \
examples/databricks/all-purpose-cluster dev \
-e AWS_REGION=${AWS_REGION} \
-e AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID} \
-e DATABRICKS_ACCOUNT_ID=${DATABRICKS_ACCOUNT_ID} \
-e DATABRICKS_AWS_ACCOUNT_ID=${DATABRICKS_AWS_ACCOUNT_ID} \
--show-queries
```

Takes its time, again verbose, concludes in:

```
2025-02-08 13:24:17,941 - stackql-deploy - INFO - ✅ successfully deleted AWS_iam_cross_account_role
2025-02-08 13:24:17,942 - stackql-deploy - INFO - deployment completed in 0:03:21.191788
🚧 teardown complete (dry run: False)
```

Success!!!

## Optional step: verify destruction with stackql

Now, let us do some sanity checks and housekeeping with `stackql`.  This is purely optional.  From the root of this repository: 

```

source examples/databricks/all-purpose-cluster/convenience.sh

stackql shell

```

This will start a `stackql` interactive shell.  Here are some commands you can run (I will not place output here):


```sql

registry pull databricks_account v24.12.00279;

registry pull databricks_workspace v24.12.00279;



select account_id, workspace_name, workspace_id, workspace_status from databricks_account.provisioning.workspaces where account_id = '<your databricks account id>';

```

## Cancel databricks subsription

This is **very** important.

Go to [the aws Marketplace manage subscriptions page](https://console.aws.amazon.com/marketplace/home#/subscriptions), navigate to databricks and then cancel the subscription.  

## Figures


![Create aws databricks subscription](/examples/databricks/all-purpose-cluster/assets/create-aws-databricks-subscription.png)

**Figure S1**: Create aws databricks subscription.

---

![Awaiting aws databricks subscription resources](/examples/databricks/all-purpose-cluster/assets/awaiting-subscription-resources.png)

**Figure S2**: Awaiting aws databricks subscription resources.

---

![Auto provisioned workspace](/examples/databricks/all-purpose-cluster/assets/auto-provisioned-worskpace.png)

**Figure S3**: Auto provisioned workspace.

---

![Capture databricks account id](/examples/databricks/all-purpose-cluster/assets/capture-databricks-account-id.png)

**Figure U1**: Capture databricks account id.

---

![Capture cross databricks aws account id](/examples/databricks/all-purpose-cluster/assets/capture-cross-databricks-aws-account-id.png)

**Figure XA1**: Capture cross databricks aws account id.

---

![Create CICD agent](/examples/databricks/all-purpose-cluster/assets/create-cicd-agent.png)

**Figure S4**: Create CICD agent.

---

![Grant account admin to CICD agent](/examples/databricks/all-purpose-cluster/assets/grant-account-admin-cicd-agent.png)

**Figure S5**: Grant account admin to CICD agent.

---

![Generate secret for CICD agent](/examples/databricks/all-purpose-cluster/assets/generate-secret-ui.png)

**Figure S6**: Generate secret for CICD agent.

---
