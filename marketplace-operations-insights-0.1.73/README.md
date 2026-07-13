# Marketplace Operation Insights

## 🚀 Quick Setup

For the fastest setup, use the automated script:

```bash
./setup.sh
```

This will set up Python 3.11, install dependencies, and create the secrets template.

## 📖 Detailed Setup Guide

For comprehensive setup instructions, especially for **PostgreSQL read replica configuration**, see:

**[LOCAL_SETUP_GUIDE.md](./LOCAL_SETUP_GUIDE.md)** - Complete guide for local development with read replica

## 🎯 Database Configuration

The application supports two database options:

- **PostgreSQL (Recommended)** - Read replica for better performance and reduced load on production
- **Redshift (Fallback)** - Original data warehouse connection

The app automatically prefers PostgreSQL when configured.

## Manual Setup (Alternative)

If you prefer manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

### Configure Secrets
```bash
mkdir -p .streamlit && cp secrets.toml.example .streamlit/secrets.toml
```

Update connection string in `.streamlit/secrets.toml` with your database credentials.

### Start Streamlit
```bash
streamlit run src/app.py
```

Enter the password in your `.streamlit/secrets.toml` file under `[auth] -> app_password`

### Streamlit Docs

https://streamlit.io/

## MOG Pax8 Docs

In order to make our documentation universally accessible and useful, we store all ADRs here:
https://github.com/pax8/mog-documents

## Architectural overview

This application is a Streamlit application that connects to Redshift to provide insights into the Marketplace
Operations data. It is a simple application that allows users to query the data and visualize it in a variety of ways.

We have structured MOI as a multi-page application, with each page corresponding to a different view of the data. This
has mostly aligned each individual page with a UAT process, rather than a specific domain concept. This is a bit of a
departure from the way we have structured other applications, but has been powerful in allowing different teams to make
rapid progress in data analysis.

In the future, we will be creating pages that are more domain-specific, such as a page for the Partner Operations team
that displays lists of Partners and their details. Other pages may include financial analysis treating time series
aggregations as a first class citizen, or a page for the Marketplace Operations team enabling automation of populating
Jira tickets with arrears errors.

### Recommendations

Please consider the Next Steps section as an advisory regarding which existing pages are likely to be deprecated in the
near future. This will help you to select your inspiration and to prioritize your work on the application.

When adding a page, you should modify the `src/app.py` file to include the new page in `pages()`. This functions as a
router for the sidebar.

You should also create a new file in the `src/pages` directory that contains the logic for the page. This file should
contain a function that returns a Streamlit component that will be rendered in the main content area of the page. This
is generally the main body of work, and likely requires some use of `queries`.

You may also create a new file in the `src/components` directory that contains any reusable work. We anticipate using
this directory for components that may be shared across multiple pages, such as when listing common domain objects like
subscription details. However, this is only recommended as a refactor step in importing someone else's behaviour, as we
prioritize YAGNI.

### Next Steps

This section was last updated in 2024Q4.

The current diagnostics pages are focused on examining specific use cases rather than providing a comprehensive domain
analysis. We will be working on creating a more comprehensive set of pages that provide a more holistic view of the
Marketplace Operations data. When creating a new page, you should consider whether your page is a diagnostic page or a
domain page. Diagnostic pages are focused on a specific use case, while domain pages are focused on a specific domain
area, such as insights. Try to create domain pages where possible.

We are planning to sunset the current diagnostics pages once their respective projects are complete, particularly EDSB
UAT. This means that we will be removing the pages from the application without providing similar replacement
functionality.

We will likely choose to retain limited, specific functionality from those pages in the form of DB and domain
components. In particular, the way we handle DB connections is going to change, in order to make better use of Streamlit
connection caching. More generally, we will move this sort of functionality into a generic Administrative Tools page
that will be accessible to all (or most) users, which also implies that the user must refresh their view after resetting
the remote cache.

## Deployment and Runtime Environment

We manage this application via Argo within the `data-platform` Bounded Context:

https://argocd.production.pax8.com/applications/marketplace-operations-insights

Within 10 minutes of creating a new GitHub Release, you should see a new ReplicaSet created in the Argo UI. This will
contain the pods that are running the Streamlit server. Note that you cannot simply mark a release as Latest in order to
roll out a new ReplicaSet - you must create a new release with a new tag. This is a limitation of our GitHub Action.

### Logs from Sumo

If you have any idea what you're looking for, you probably want to use Sumo. The logs are available under
`service=marketplace-operations-insights`:
https://pax8.us2.sumologic.com/ui/#/search/create?id=bu2qxHjrrv9tB7NCvuwyo07PxZkCzvicTvBH2sdY

You can filter by the `pod` field to find the logs for a particular pod, if you only want to check a specific recent
release. Note that the logs are not available in real-time, so you may need to wait a few minutes for them to appear.

### Logs from Argo

Server-side logs containing the output of a currently active Streamlit server can be reviewed by opening the ReplicaSet
in the Argo UI, which will show the logs for each pod. You may view the logs for the individual replicas by viewing the
pod dialog under the currently active `rs`. Note that old RevisionSets are not immediately cleared out and simply have
no active pods, so you should be able to find the active pods highlighted by the top of a substantial list.

### Logs from kubectl

Be advised that our pods are running against production data, so this requires `kubectx production`, which may not be
readily available.

The logs are also available via the `kubectl` CLI, e.g.
`kubectl logs -f -l app=marketplace-operations-insights --all-containers=true`. This is significantly more versatile in
enabling local scripting. If using `kubectl logs -p <pod-name>`, pods are named e.g.
`marketplace-operations-insights-68d7c84bb7-jplrl` - try `kubectl get pods | grep "<app-name>"` to find the pod name.
