#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "@aws-cdk/core";
import { ThroatStack } from "../src/throat-stack";

const app = new cdk.App();
const neededContext = {
  base: app.node.tryGetContext("baseDns"),
  subname: app.node.tryGetContext("subname"),
  databaseName: app.node.tryGetContext("databaseName"),
  databaseUsername: app.node.tryGetContext("databaseUsername"),
};

Object.entries(neededContext).forEach(([key, value]) => {
  if (value == null) {
    throw Error(`${key} needed in context`);
  }
});

new ThroatStack(app, `ThroatStack-${neededContext["subname"]}`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
