# Azure Credentials Request

## What We Need From You

We'll create all the Azure infrastructure ourselves via Bicep (IaC). We just need access.

### 1. An Azure Subscription We Can Use

Your MSDN/Visual Studio Enterprise sub works great ($150/mo free credits — more than enough for dev).

Share these two values — **Subscription ID** and **Tenant ID**:

**Portal:**
1. Go to [portal.azure.com](https://portal.azure.com)
2. Search "Subscriptions" in the top search bar
3. Click your subscription — the **Subscription ID** is right there on the Overview page
4. For **Tenant ID**: click your profile icon (top-right) → "Switch directory" — the Tenant ID is listed next to each directory. Or go to **Microsoft Entra ID** → Overview → Tenant ID

**CLI:**
```bash
az account show --query "{subscriptionId:id, tenantId:tenantId}" -o table
```

### 2. Invite Brandon as a Contributor

**Portal:**
1. Go to [portal.azure.com](https://portal.azure.com) → **Subscriptions** → click your subscription
2. Left sidebar → **Access control (IAM)**
3. Click **+ Add** → **Add role assignment**
4. Role tab: search "Contributor" → select it → Next
5. Members tab: click **+ Select members** → search Brandon's email → select → Next
6. Review + assign

**CLI:**
```bash
az role assignment create \
  --assignee <brandon-email> \
  --role "Contributor" \
  --scope /subscriptions/<sub-id>
```

That's it for permissions. Contributor lets us create resource groups, deploy services, and manage everything via code.

### 3. Confirm Azure OpenAI Access

Azure OpenAI requires an approved subscription. Most MSDN Enterprise subs have it.

**Portal:**
1. Go to [portal.azure.com](https://portal.azure.com)
2. Search "Azure OpenAI" in the top search bar
3. Click **+ Create** — if you can see the creation form and select your subscription, you're good
4. (You don't need to actually create it — just confirm you have access. We'll create it via Bicep.)

**CLI:**
```bash
az cognitiveservices account list-kinds | grep OpenAI
```

If it's not enabled, request access at: https://aka.ms/oai/access

### What We'll Create (You Don't Have To)

Once we have Contributor access, our Bicep templates handle everything:
- Resource Group (`rg-sermon-rating-dev`)
- Azure OpenAI + GPT-4o deployment
- Azure AI Speech Service
- Cosmos DB (serverless)
- Azure Functions
- Blob Storage
- Key Vault
- Static Web Apps

### Estimated Cost

~$20-50/mo during dev. Well within MSDN credits.

### How to Share Credentials Safely

DM Brandon directly — not in a public channel:
- Subscription ID
- Tenant ID
- Confirm Contributor role assigned
- Confirm Azure OpenAI is available on the sub
