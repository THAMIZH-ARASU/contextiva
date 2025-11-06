# Infrastructure and Deployment

## Infrastructure as Code
- **Tool**: Docker (docker-compose.yml) for local development; Kubernetes YAML (k8s/) for production deployment.
- **Location**: docker-compose.yml at root; k8s/ directory at root.
- **Approach**: The docker-compose.yml file defines the api, postgres, and redis services for a complete, self-contained local development environment (Story 1.1). The k8s/ manifests define the production deployments, services, and configurations.

## Deployment Strategy
- **Strategy**: Rolling updates will be the default strategy for the Kubernetes deployment to ensure zero downtime.
- **CI/CD Platform**: GitHub Actions (inferred from the .github/ folder in the Source Tree).
- **Pipeline Configuration**: The pipeline will be defined in .github/workflows/. It will be responsible for running tests (lint, format, type check, unit, integration, E2E), building, and pushing a new Docker image for the api service to a container registry (e.g., Docker Hub, AWS ECR, GCP GCR), and then applying the k8s/ manifests to deploy the new image.

## Environments
- `development`: Local machine, managed by docker-compose up.
- `staging`: A production-like Kubernetes cluster used for testing E2E and validating new features before release.
- `production`: The live Kubernetes cluster serving end-users.

## Environment Promotion Flow
 
```Plaintext
1. Local `feature/*` branch -> PR -> `develop`
2. `develop` branch merges -> CI/CD pipeline runs all tests
3. On Test Pass -> Deploy to `staging` environment
4. Manual Verification / E2E Tests on `staging`
5. `develop` branch merges to `main` (or tag release)
6. `main` branch push -> CI/CD pipeline deploys to `production`
```

## Rollback Strategy
- **Primary Method**: Re-deploying the previous stable Docker image tag via Kubernetes (kubectl rollout undo...).
- **Trigger Conditions**: Critical error rate spike in observability tools, high percentage of failed health checks after deployment, or critical feature failure reported by E2E tests.
- **Recovery Time Objective**: < 15 minutes.
