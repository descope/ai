# Remote MCP Server using Descope's MCP Auth SDK and AWS Lambda

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction
This repository contains an example **Remote MCP** [**(Model Context Protocol)**](https://modelcontextprotocol.io/introduction) server with authentication, built using [**Descope's MCP Auth SDK**](https://www.descope.com/blog/post/mcp-auth-sdk) and deployed on [AWS Lambda](https://aws.amazon.com/lambda/) with [API Gateway](https://aws.amazon.com/api-gateway/).

**AWS Lambda** is a serverless compute service that runs your code in response to events and automatically manages the underlying compute resources. Combined with **API Gateway**, it provides a fully managed, scalable, and secure way to expose your MCP server as a REST API.

The MCP server exposes an interface between LLMs or MCP clients (such as Claude) and the **National Weather Service (NWS) API**. This enables your LLM applications to fetch weather data, including:
- Weather forecasts for specific locations
- Weather alerts for states

This example can be easily customized to integrate with arbitrary backend services, APIs, workflows, or data sources, allowing you to quickly set up and deploy your own MCP server with built-in Descope authentication.

## Preview the Application
This Remote MCP Server is deployed to AWS Lambda here: [https://ta67b5b2b8.execute-api.us-west-1.amazonaws.com](https://ta67b5b2b8.execute-api.us-west-1.amazonaws.com)

You can connect to the server using the [Cloudflare Playground](https://playground.ai.cloudflare.com/), [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) or any other MCP client such as Claude Desktop or Cursor. Be sure to include the `/mcp` path in the connection URL, i.e, `https://ta67b5b2b8.execute-api.us-west-1.amazonaws.com/mcp`

## Features

- Allows LLMs and MCP clients to fetch:
  - Weather forecasts for any location in the United States
  - Weather alerts for any state
  
  Using the [National Weather Service API](https://www.weather.gov/documentation/services-web-api).
- Secure authentication for the MCP server using Descope.
- MCP Authorization Compliant.
- Serverless deployment with automatic scaling.

## Requirements

Before proceeding, make sure you have the following:

- [Node.js](https://nodejs.org/) (version 18 or later)
- A valid Descope [Project ID](https://app.descope.com/settings/project) and [Management Key](https://app.descope.com/settings/company/managementkeys)
- The Descope Inbound Apps feature enabled
- An [AWS account](https://aws.amazon.com/) with:
    - [AWS CLI](https://aws.amazon.com/cli/) installed and configured (`aws configure`)
    - Permission to deploy Lambda functions, API Gateway, and Secrets Manager
    - [AWS CDK](https://aws.amazon.com/cdk/) installed globally (`npm install -g aws-cdk`)
- Docker installed (for Lambda bundling)
- Git installed

## Project Setup

This section explains the key components needed to set up an MCP server with AWS Lambda deployment. If you're using this repository, you can skip to the [Running the Server locally](#running-the-server-locally) section.

### Project Structure
```
aws-mcp-server/
├── src/
│   ├── index.ts          # Main Express server with MCP endpoints
│   ├── lambda.ts         # Lambda handler for AWS deployment
│   └── tools.ts          # MCP tools implementation
├── lib/
│   └── cdk-stack.ts      # AWS CDK infrastructure definition
├── bin/
│   └── cdk.ts            # CDK app entry point
├── package.json
├── tsconfig.json
└── cdk.json
```

### Key Components Explained

#### 1. **Main Server (`src/index.ts`)**
- **Purpose**: Express server that handles MCP protocol requests and authentication
- **Key Features**: 
  - MCP endpoint (`/mcp`) for protocol communication
  - OAuth metadata endpoints for Descope integration
  - Weather server initialization and connection
- **Adaptation**: Replace the weather tools with your own MCP tools

#### 2. **Lambda Handler (`src/lambda.ts`)**
- **Purpose**: AWS Lambda entry point that bridges API Gateway to your Express server
- **Key Features**:
  - Loads secrets from AWS Secrets Manager on cold start
  - Wraps Express app with serverless-http for Lambda compatibility
  - Handles environment variable setup
- **Adaptation**: Update secret names and environment variables for your use case

#### 3. **MCP Tools (`src/tools.ts`)**
- **Purpose**: Implements the actual MCP tools that your server provides
- **Key Features**:
  - Weather forecast and alerts tools using NWS API
  - Proper error handling and response formatting
  - TypeScript types for tool parameters
- **Adaptation**: Replace with your own API integrations and tools

#### 4. **CDK Stack (`lib/cdk-stack.ts`)**
- **Purpose**: Infrastructure as code that defines your AWS resources
- **Key Features**:
  - Lambda function with Node.js runtime
  - API Gateway with CORS support
  - Secrets Manager integration
  - IAM permissions for secure access
- **Adaptation**: Modify resource names, memory allocation, and permissions as needed

#### 5. **Configuration Files**
- **`tsconfig.json`**: TypeScript compilation settings
- **`cdk.json`**: CDK app entry point configuration
- **`package.json`**: Dependencies and build scripts

### Setup Steps

1. **Initialize project** with `npm init` and install dependencies
2. **Create TypeScript config** for proper compilation
3. **Set up CDK** for infrastructure management
4. **Implement your MCP tools** in `src/tools.ts`
5. **Configure authentication** with your Descope credentials
6. **Deploy infrastructure** using CDK

### Dependencies Overview

**Runtime Dependencies**:
- `@descope/mcp-express`: Descope authentication for MCP
- `@modelcontextprotocol/sdk`: MCP protocol implementation
- `express` & `serverless-http`: Web server and Lambda compatibility
- `@aws-sdk/client-secrets-manager`: AWS secrets management

**Development Dependencies**:
- `aws-cdk-lib`: AWS CDK for infrastructure
- `typescript`: TypeScript compilation
- `@types/*`: Type definitions for TypeScript

## Running the Server locally
To get the MCP server running locally, follow the following steps:

1. Clone the repository and `cd` into it:
```bash
git clone <your-repo-url>
cd aws-mcp-server
```

2. Add the environment variables in a `.env` file at the root:
```bash
# Copy the example file and update with your values
cp .env.example .env
```

Then edit the `.env` file with your actual values:
```bash
DESCOPE_PROJECT_ID=      # Your Descope project ID
DESCOPE_MANAGEMENT_KEY=  # Your Descope management key
SERVER_URL=              # The URL where your server is hosted (http://localhost:3000 for local)
```

3. Install dependencies:
```bash
npm install
```

4. Build and start the server:
```bash
npm run build
npm run start
```

The server will start locally on port 3000 (or the port specified in your environment variables).
Navigating to http://localhost:3000 will show you the status of the MCP server.

## Deploying the Server to AWS Lambda
Now that you have the server working locally, you can begin the process of deploying it to AWS Lambda using AWS CDK.

### Step 1: Setup AWS Secrets Manager
First, you need to store your Descope credentials securely in AWS Secrets Manager:

1. **Create a secret in AWS Secrets Manager**:
```bash
aws secretsmanager create-secret \
  --name "aws-weather-mcp-server" \
  --description "Descope credentials for MCP server" \
  --secret-string '{
    "DESCOPE_PROJECT_ID": "your-descope-project-id",
    "DESCOPE_MANAGEMENT_KEY": "your-descope-management-key",
    "SERVER_URL": "https://your-api-gateway-url.execute-api.region.amazonaws.com"
  }'
```

**Note**: The `SERVER_URL` will be updated after deployment with the actual API Gateway URL.

### Step 2: Deploy with AWS CDK
The project uses AWS CDK for infrastructure as code. The deployment will create:
- Lambda function with your MCP server
- API Gateway for HTTP endpoints
- IAM roles and permissions
- Secrets Manager access

1. **Deploy the stack**:
```bash
npm run cdk-deploy
```

2. **Get the deployment URL**: After successful deployment, CDK will output the API Gateway URL. You can also find it in the AWS Console under API Gateway.

3. **Update the secret with the correct SERVER_URL**:
```bash
aws secretsmanager update-secret \
  --secret-id "aws-weather-mcp-server" \
  --secret-string '{
    "DESCOPE_PROJECT_ID": "your-descope-project-id",
    "DESCOPE_MANAGEMENT_KEY": "your-descope-management-key",
    "SERVER_URL": "https://your-actual-api-gateway-url.execute-api.region.amazonaws.com"
  }'
```

### Step 3: Verify Deployment
Test your deployed server:
```bash
curl -X GET https://your-api-gateway-url.execute-api.region.amazonaws.com/
```

You should see: `{"status":"MCP Server is running"}`

## API Endpoints
- `GET /`: A health check endpoint that returns the server status.
- `POST /mcp`: Handles incoming messages for the MCP protocol.
- `GET /.well-known/oauth-protected-resource`: OAuth protected resource metadata.
- `GET /.well-known/oauth-authorization-server`: OAuth authorization server metadata.

## Available Tools
The MCP server provides the following tools:

### `get-forecast`
Get weather forecast for a specific location.
- **Parameters**:
  - `latitude` (number): Latitude of the location (-90 to 90)
  - `longitude` (number): Longitude of the location (-180 to 180)
- **Returns**: Detailed weather forecast including temperature, wind, and conditions

### `get-alerts`
Get weather alerts for a specific state.
- **Parameters**:
  - `state` (string): Two-letter state code (e.g., "CA", "NY")
- **Returns**: Active weather alerts for the specified state

## Authentication
The server uses [Descope](https://www.descope.com/) for authentication. All MCP endpoints except the authentication router require a valid bearer token.

## Infrastructure Details
The CDK stack creates the following AWS resources:

- **Lambda Function**: Runs your MCP server code
- **API Gateway**: Provides HTTP endpoints and handles routing
- **Secrets Manager**: Securely stores Descope credentials
- **IAM Roles**: Provides necessary permissions for Lambda to access secrets

## Local Development
For local development, you can run the server directly without AWS:

```bash
npm run dev
```

This will start the server on port 3000 with hot reloading.

## Troubleshooting

### Common Issues

1. **500 Internal Server Error**: Check CloudWatch logs for the Lambda function
2. **Authentication Errors**: Verify your Descope credentials in Secrets Manager
3. **CORS Issues**: The API Gateway is configured to allow all origins for development

### Viewing Logs
To view Lambda function logs:
```bash
aws logs tail /aws/lambda/LambdaMcpServerStack-mcpFunction --follow
```

## Contributing
Feel free to submit issues and enhancement requests!

## License
This project is licensed under the MIT License.
