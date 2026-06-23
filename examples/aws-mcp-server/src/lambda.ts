import serverless from 'serverless-http';
import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { SecretsManagerClient, GetSecretValueCommand } from "@aws-sdk/client-secrets-manager";

// Initialize Secrets Manager client
const secretsClient = new SecretsManagerClient();

// Function to fetch secrets and set environment variables
async function loadSecrets() {
    const secretName = process.env.DESCOPE_SECRET_NAME;
    if (!secretName) {
        console.error('DESCOPE_SECRET_NAME environment variable is not set');
        return;
    }

    try {
        const command = new GetSecretValueCommand({ SecretId: secretName });
        const response = await secretsClient.send(command);
        
        if (response.SecretString) {
            const secrets = JSON.parse(response.SecretString);
            
            // Set environment variables from secrets
            process.env.DESCOPE_PROJECT_ID = secrets.DESCOPE_PROJECT_ID;
            process.env.DESCOPE_MANAGEMENT_KEY = secrets.DESCOPE_MANAGEMENT_KEY;
            
            // Prefer environment SERVER_URL if set, else use secret
            process.env.SERVER_URL = process.env.SERVER_URL || secrets.SERVER_URL;
            
            console.log('Secrets loaded successfully');
        } else {
            console.error('Secret string is empty');
        }
    } catch (error) {
        console.error('Error loading secrets:', error);
        // Don't throw error, continue without secrets if needed
    }
}

// Initialize secrets and serverless handler
let serverlessHandler: any = null;

export const handler = async (event: APIGatewayProxyEvent, context: Context): Promise<APIGatewayProxyResult> => {
    console.log('Lambda handler called with event:', JSON.stringify(event, null, 2));
    
    try {
        // Load secrets and initialize handler on first invocation (cold start)
        if (!serverlessHandler) {
            console.log('Initializing serverless handler...');
            await loadSecrets();
            
            // Import the handler from index.js
            const { handler: expressHandler } = await import('./index.js');
            serverlessHandler = expressHandler;
            console.log('Serverless handler initialized successfully');
        }

        const result = await serverlessHandler(event, context);
        console.log('Handler result:', JSON.stringify(result, null, 2));
        return result as APIGatewayProxyResult;
    } catch (error) {
        console.error('Error in Lambda handler:', error);
        return {
            statusCode: 500,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                error: 'Internal server error',
                message: error instanceof Error ? error.message : 'Unknown error'
            })
        };
    }
};