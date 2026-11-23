import { defineRailway, github, project, service } from "railway/iac";

// Infrastructure definition for the OpenHydra production service.
// This file replaces the legacy railway.json. Each value keeps the deployed behavior.
export default defineRailway(() => {
  // Adopt the existing service by its exact name.
  const app = service("OpenHydra", {
    source: github("carloborodulin/OpenHydra", {
      branch: "main", // Keep the current production source branch.
      checkSuites: false, // Keep the trigger timing during the migration.
    }),
    build: {
      buildEnvironment: "V3", // Match the effective deployment manifest.
      builder: "DOCKERFILE", // The data stage builds the warehouse before the service starts.
      dockerfilePath: "Dockerfile", // Three-stage build at the repository root.
    },
    deploy: {
      runtime: "V2", // Keep the deployed runtime.
      healthcheckPath: "/health", // The probe reads the offenses mart.
      healthcheckTimeout: 120, // Keep the startup allowance in seconds.
      restartPolicyType: "ON_FAILURE", // Keep the legacy restart contract.
      restartPolicyMaxRetries: 3, // Keep the retry bound from railway.json.
    },
    replicas: { "us-west2": 1 }, // Keep one instance in the current region.
    networking: {
      privateNetworkEndpoint: "openhydra", // Keep the internal hostname.
      serviceDomains: { "openhydra-production.up.railway.app": {} }, // Keep public routing.
    },
  });
  return project("OpenHydra", {
    // The operator owns the credential and the base URL in Railway.
    variables: { managed: false },
    resources: [app], // This repository owns the one service in the environment.
  });
});
