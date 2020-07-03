#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "@aws-cdk/core";
import { ThroatStack } from "../src/throat-stack";

const app = new cdk.App();
new ThroatStack(app, "StackStack");
