# Remote MCP Server using Descope's MCP Auth SDK and Google CloudRun

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction
This repository contains an example **Remote MCP** [**(Model Context Protocol)**](https://modelcontextprotocol.io/introduction) server with authentication, built using [**Descope’s MCP Auth SDK**](https://www.descope.com/blog/post/mcp-auth-sdk) and deployed on [Google Cloud Run](https://cloud.google.com/run).

**Google Cloud Run** is a fully managed compute platform that automatically scales your containerized applications, and provides Serverless deployment, Autoscaling, fast deployments, and a Public URL for your application.

The MCP server exposes an interface between LLMs or MCP clients (such as Claude) and the **Nutritionix API**. This enables your LLM applications to fetch nutritional and exercise data, including:
- Macronutrient information for specific meals
- Calorie expenditure estimates for workouts

This example can be easily customized to integrate with arbitrary backend services, APIs, workflows, or data sources, allowing you to quickly set up and deploy your own MCP server with built-in Descope authentication.


## Preview the Application
This Remote MCP Server is deployed to Google CloudRun here: [https://nutrition-mcp-server-998218601126.us-central1.run.app](https://nutrition-mcp-server-998218601126.us-central1.run.app)

You can connect to the server using the [Cloudflare Playground](https://playground.ai.cloudflare.com/), [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) or any other MCP client such as Claude Desktop or Cursor. Be sure to include the `/mcp` path in the connection URL, i.e, `https://nutrition-mcp-server-998218601126.us-central1.run.app/mcp`

## Features

- Allows LLMs and MCP clients to fetch:
  - accurate nutritional information for any meal, and 
  - calorie expenditure estimates for exercises and activities
  
  Using the [Nutrionix API](https://docx.syndigo.com/developers/docs/nutritionix-api-guide).
- Secure authentication for the MCP server using Descope.
- MCP Authorization Compliant.

## Requirements

Before proceeding, make sure you have the following:

- [Node.js](https://nodejs.org/) (version 18 or later)
- A valid Descope [Project ID](https://app.descope.com/settings/project) and [Management Key](https://app.descope.com/settings/company/managementkeys)
- The Descope Inbound Apps feature enabled
- A [Google Cloud account](https://cloud.google.com/) with:
    - Billing enabled
    - [Google Cloud SDK](https://cloud.google.com/sdk/docs/install-sdk) installed and configured (gcloud init)
    - Permission to deploy services to [Cloud Run](https://cloud.google.com/run)
    - Access to a container registry such as [Artifact Registry](https://cloud.google.com/artifact-registry) to store your built Docker images
- Free Nutrionix Credentials (app id, and app key), which you can get by [signing up](https://developer.nutritionix.com/signup).
- Docker installed
- Git installed

## Running the Server locally
To get the MCP server running locally, follow the following steps:

1. Clone the repository, and `cd` into `examples/mcp-server-cloudrun`
```bash
git clone https://github.com/descope/ai.git
cd ai/examples/mcp-server-cloudrun
```

2. add the environment variables in a `.env` file at the root:
You can copy the .env.example file, 
```bash
cp .env.example .env
```

and then edit the fields below:
```bash
DESCOPE_PROJECT_ID=      # Your Descope project ID
DESCOPE_MANAGEMENT_KEY=  # Your Descope management key
SERVER_URL=              # The URL where your server is hosted

# Your Nutrionix credentials (app ID, and app key), get it by signing up at https://developer.nutritionix.com/signup
NUTRIONIX_APP_ID=        
NUTRIONIX_APP_KEY=
```

3. Then, install dependencies:
```bash
npm install
```

4. The setup is complete! To run the server locally:
```bash
npm run build
npm run start
```

The server will start locally on port 3000 (or the port specified in your environment variables).
Navigating to http://localhost:3000 will show you the features of the MCP server, along with instructions on how to connect it to MCP Clients like Claude, Cursor, etc.

## Deploying the Server to Google Cloud Run
Now that you have the server working locally, you can begin the process of deploying it to Google Cloud Run. Cloud Run will build, host, and serve your container, providing a **secure public URL** that anyone can access.

### Step 1: Building and Pushing a Docker Image
We will start by containerizing the application using [**Docker**](https://www.docker.com/). A sample Dockerfile is included in this repository; you do not need to modify it.

#### **1. Build your image locally**: 
Open your terminal in the project directory and run:
```bash
docker build -t nutrition-mcp-server . 
```
This command builds your Docker image and tags it as `nutrition-mcp-server`.

#### **2. Setup your Google Cloud Project ID on the `gcloud` cli**

You can select a Project, and get its Project ID from the [GCloud Project Selector Page](https://console.cloud.google.com/projectselector2/home/dashboard)

(recommended) For your convenience, first set up an environment variable called `GCLOUD_PROJECT_ID`, which you can reference in the later commands:
```bash
export GCLOUD_PROJECT_ID="your gcloud project id"
```
Now, you can use the environment variable `$GCLOUD_PROJECT_ID` in the terminal commands.

Now, setup the project ID in your GCloud config by running:
```bash
gcloud config set project $GCLOUD_PROJECT_ID
```

#### **3. Create an Artifact Registry Repository**: You need a container repository to store your image. Create one with
```bash
gcloud artifacts repositories create remote-mcp-servers \
  --repository-format=docker \
  --location=us-central1 \
  --description="Repository for remote MCP servers" \
  --project=$GCLOUD_PROJECT_ID # replace with your google cloud project id, if not automatically populated
```

#### **4. Build and push the image** to Artifact Registry using Cloud Build
Submit the build and push the container to your repository:
```bash
gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/$GCLOUD_PROJECT_ID/remote-mcp-servers/nutrition-mcp-server:latest
```

### Step 2: Create your Cloud Run Application
#### **1. Create .env.yaml config file for CloudRun secrets**

First, we will setup a .env.yaml file which allows us to securely pass secrets to our Cloud Run Service.
You can first copy the existing `.env.yaml.example` file
```bash
cp .env.yaml.example .env.yaml
```
and then, update the fields in your `.env.yaml` file
```yaml
DESCOPE_PROJECT_ID: "<your descope project id>"
DESCOPE_MANAGEMENT_KEY: "<your descope management key>"
SERVER_URL: "http://localhost:3000" # For local development
# For production (DON'T forget to replace with your CloudRun worker URL)
NUTRIONIX_APP_ID: "<app id>"
NUTRIONIX_APP_KEY: "<app key>"
```
We will mention the above `.env.yaml` file in our command below

#### **2. Deploy as Cloud Run Service**
Since our image is now stored in Artifact Registry, you can deploy it as a Cloud Run service:
```bash
gcloud run deploy nutrition-mcp-server \
  --image us-central1-docker.pkg.dev/descope-mcp/remote-mcp-servers/nutrition-mcp-server:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --env-vars-file .env.yaml 
```
The reason we use the `--allow-unauthenticated` flag is to make the Cloud Run service **publicly accessible to anyone** without requiring Google Cloud IAM authentication.

Authentication is handled within the application itself using Descope. 

#### **3. Verify that the Deployment is complete**: After running the above command, you will get a message on the terminal, similar to:
```bash
Done.                                                                      
Service [nutrition-mcp-server] revision [nutrition-mcp-server-00003-xf9] has been deployed and is serving 100 percent of traffic.
Service URL: https://nutrition-mcp-server-998218601126.us-central1.run.app
```
Congratulations! You now have a remote MCP server deployed, and publicly accesible on the Service URL. You can now visit the URL mentioned, and connect the MCP server to an MCP Client like [CloudFlare Playground](https://playground.ai.cloudflare.com/), Claude Desktop, Cursor, etc.

## API Endpoints
- `GET /`: A homepage for the application, describing the features of the MCP server, and how to connect it to various MCP clients.
- `POST /mcp`: Handles incoming messages for the MCP protocol.

## Authentication
The server uses [Descope](https://www.descope.com/) for authentication. All MCP endpoints except the authentication router require a valid bearer token.
