#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { LambdaMcpServerStack } from '../lib/cdk-stack';

const app = new cdk.App();
new LambdaMcpServerStack(app, 'LambdaMcpServerStack');
