#!/bin/bash
# Rollback Script
# ===============
# Instantly rollback to a previous Cloud Run revision.
#
# Usage:
#   ./scripts/rollback.sh [REVISION_NAME]
#
# If no revision is specified, rolls back to the most recent inactive revision.
#
# Safety:
#   - Prompts for confirmation
#   - Takes a snapshot before rollback
#   - Verifies health after rollback

set -euo pipefail

SERVICE="accountability-agent"
REGION="us-central1"
PROJECT="accountability-agent"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔄 Accountability Agent Rollback"
echo "=================================="

# Get target revision
if [ $# -ge 1 ]; then
    TARGET_REVISION="$1"
    echo "Target revision: $TARGET_REVISION"
else
    echo "Finding most recent inactive revision..."
    TARGET_REVISION=$(gcloud run revisions list \
        --service="$SERVICE" \
        --region="$REGION" \
        --format="value(metadata.name)" \
        | grep -v "$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.traffic[0].revisionName)')" \
        | head -1)
    echo "Target revision: $TARGET_REVISION"
fi

# Verify revision exists
if ! gcloud run revisions describe "$TARGET_REVISION" --service="$SERVICE" --region="$REGION" >/dev/null 2>&1; then
    echo -e "${RED}❌ Revision $TARGET_REVISION not found${NC}"
    exit 1
fi

# Snapshot current state
echo ""
echo "📸 Snapshotting current service config..."
SNAPSHOT_FILE="/tmp/accountability-agent.pre-rollback.$(date +%Y%m%d-%H%M%S).yaml"
gcloud run services describe "$SERVICE" --platform=managed --region="$REGION" --format=export > "$SNAPSHOT_FILE"
echo "   Saved to: $SNAPSHOT_FILE"

# Get current revision
CURRENT_REVISION=$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.traffic[0].revisionName)')
echo "   Current revision: $CURRENT_REVISION"

# Confirm
echo ""
echo -e "${YELLOW}⚠️  You are about to roll back:${NC}"
echo "   From: $CURRENT_REVISION"
echo "   To:   $TARGET_REVISION"
echo ""
read -p "Type 'rollback' to confirm: " CONFIRM
if [ "$CONFIRM" != "rollback" ]; then
    echo -e "${RED}❌ Rollback cancelled${NC}"
    exit 1
fi

# Perform rollback
echo ""
echo "🚀 Rolling back..."
gcloud run services update-traffic "$SERVICE" \
    --region="$REGION" \
    --to-revisions="$TARGET_REVISION=100" \
    --platform=managed

# Verify
echo ""
echo "🔍 Verifying rollback..."
NEW_REVISION=$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.traffic[0].revisionName)')
if [ "$NEW_REVISION" == "$TARGET_REVISION" ]; then
    echo -e "${GREEN}✅ Rollback successful!${NC}"
    echo "   Now serving: $NEW_REVISION"
else
    echo -e "${RED}❌ Rollback verification failed${NC}"
    echo "   Expected: $TARGET_REVISION"
    echo "   Got:      $NEW_REVISION"
    exit 1
fi

# Health check
echo ""
echo "🏥 Health check..."
HEALTH_URL="https://accountability-agent-450357249483.us-central1.run.app/health"
if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Health endpoint responding${NC}"
else
    echo -e "${RED}❌ Health endpoint NOT responding${NC}"
    echo "   Consider rolling forward again:"
    echo "   gcloud run services update-traffic $SERVICE --region=$REGION --to-revisions=$CURRENT_REVISION=100"
    exit 1
fi

echo ""
echo "=================================="
echo -e "${GREEN}Rollback complete${NC}"
echo "Rolled back to: $TARGET_REVISION"
echo "Snapshot saved: $SNAPSHOT_FILE"
