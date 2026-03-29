# Azure Deployment Strategy: QPilot 🚀

## 1. Branch Structure
- **`dev-qpilot`**: Every push triggers a build/deploy to **Development**.
- **`prod-qpilot`**: Every push/merge triggers **Production**.

## 2. Infrastructure Setup (One-Time)
You will need to run these commands *once* via your Azure CLI to prepare the ACA environment:

```bash
# Variables
ACR_NAME="qpilotreg"
RG="qpilot-rg"
LOCATION="eastus"

# Create ACR
az acr create --resource-group $RG --name $ACR_NAME --sku Basic

# Create Environment
az containerapp env create --name qpilot-env --resource-group $RG --location $LOCATION

# Create Stubs (initial apps)
az containerapp create --name qpilot-backend-dev --resource-group $RG --environment qpilot-env --image $ACR_NAME.azurecr.io/qpilot-backend:latest --target-port 8000 --ingress external
az containerapp create --name qpilot-frontend-dev --resource-group $RG --environment qpilot-env --image $ACR_NAME.azurecr.io/qpilot-frontend:latest --target-port 3000 --ingress external
```

## 3. GitHub Actions Configuration
I have optimized the `.github/workflows/deploy.yml` to handle build-once, deploy-many logic if needed, or separate environment-specific files.

### Required Secrets
Ensure these are in your GitHub repo:
- `AZURE_CREDENTIALS` (Service Principal JSON)
- `ACR_NAME`
- `RG`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `AZURE_STORAGE_CONNECTION_STRING`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`

---
> [!TIP]
> Use `az ad sp create-for-rbac --name "github-actions-qpilot" --role contributor --scopes /subscriptions/{sub-id}/resourceGroups/{rg-name} --sdk-auth` to get your `AZURE_CREDENTIALS`.
