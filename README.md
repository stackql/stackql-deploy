# stackql-deploy

```
stackql-deploy {command} {environment} {stack_dir} [--dry-run] [--on-failure=rollback] [--env-file=.env] [-e FRED=fred]
stackql-deploy deploy prd activity_monitor
stackql-deploy test prd activity_monitor
stackql-deploy teardown prd activity_monitor
```

to test locally :

```
pip install -e .
```
