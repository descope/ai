import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as nodejs from 'aws-cdk-lib/aws-lambda-nodejs';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as path from 'path';

export class LambdaMcpServerStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
      super(scope, id, props);

      const descopeSecret = secretsmanager.Secret.fromSecretNameV2(this, 'descopeSecret', 'aws-weather-mcp-server');
  
      const mcpApi = new apigatewayv2.HttpApi(this, 'mcpApi', {
        corsPreflight: {
          allowOrigins: ['*'],
          allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token', 'X-Amz-User-Agent'],
          allowMethods: [apigatewayv2.CorsHttpMethod.GET, apigatewayv2.CorsHttpMethod.POST]
        }
      });

      const mcpFunction = new nodejs.NodejsFunction(this, 'mcpFunction', {
        runtime: lambda.Runtime.NODEJS_22_X,
        memorySize: 1024,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join(__dirname, '../src/lambda.ts'),
        handler: 'handler',
        environment: {
            DESCOPE_SECRET_NAME: 'aws-weather-mcp-server',
            DESCOPE_BASE_URL: 'https://api.descope.com',
            NODE_ENV: 'production'
        },
        bundling: {
          forceDockerBundling: false
        }
      });

      // Grant Lambda permission to read the secret
      descopeSecret.grantRead(mcpFunction);
  
      // Create a Lambda integration for the mcpFunction
      const mcpIntegration = new integrations.HttpLambdaIntegration('mcpFunctionIntegration', mcpFunction);
      
      // Add a catch-all route that forwards any request to the mcpFunction
      mcpApi.addRoutes({
        path: '/{proxy+}',
        integration: mcpIntegration
      });

      // Update the Lambda environment with the API Gateway URL after it's created
      mcpFunction.addEnvironment('SERVER_URL', mcpApi.apiEndpoint);
  
      new cdk.CfnOutput(this, 'mcpApiUrl', {
        value: mcpApi.apiEndpoint,
        description: 'MCP Server API Gateway URL (will change on each deployment)'
      });

      // Add a note about custom domain setup
      new cdk.CfnOutput(this, 'customDomainNote', {
        value: 'To get a consistent URL, set up a custom domain with Route53 and ACM certificate',
        description: 'Custom Domain Setup Instructions'
      });
    }
  }

