#!/bin/bash
# Script para testar o endpoint de streaming SSE

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Test Streaming SSE Endpoint          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if API is running
echo -e "${YELLOW}[1/4] Checking if backend is running...${NC}"
if curl -s http://localhost:8000/api/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not running!${NC}"
    echo "Start it with: docker-compose up backend"
    exit 1
fi
echo ""

# Get token (you need to replace with actual credentials)
echo -e "${YELLOW}[2/4] Getting authentication token...${NC}"
echo "Note: Update this script with your actual credentials"

# Example token request (adjust as needed)
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "marco", "password": "your_password"}' 2>/dev/null)

if [ $? -eq 0 ]; then
    TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access":"[^"]*' | grep -o '[^"]*$')
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}✗ Failed to get token. Check credentials.${NC}"
        echo "Response: $TOKEN_RESPONSE"
        echo ""
        echo "Trying without authentication (will likely fail)..."
        TOKEN="test_token"
    else
        echo -e "${GREEN}✓ Token obtained${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Could not obtain token, proceeding without auth${NC}"
    TOKEN="test_token"
fi
echo ""

# Test GET endpoint
echo -e "${YELLOW}[3/4] Testing GET endpoint (simple)...${NC}"
echo "Request: GET /api/chat/stream/?message=Olá"
echo ""

curl -N -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/chat/stream/?message=Olá" \
  2>/dev/null &

CURL_PID=$!
sleep 10
kill $CURL_PID 2>/dev/null
echo ""
echo -e "${GREEN}✓ GET endpoint test completed${NC}"
echo ""

# Test POST endpoint
echo -e "${YELLOW}[4/4] Testing POST endpoint (with history)...${NC}"
echo "Request: POST /api/chat/stream/"
echo ""

curl -N -X POST http://localhost:8000/api/chat/stream/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Qual a capital de Portugal?",
    "history": [
      {"role": "user", "content": "Olá"},
      {"role": "assistant", "content": "Olá! Como posso ajudar?"}
    ]
  }' \
  2>/dev/null &

CURL_PID=$!
sleep 10
kill $CURL_PID 2>/dev/null
echo ""
echo -e "${GREEN}✓ POST endpoint test completed${NC}"
echo ""

# Summary
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Test Summary                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "If you saw SSE events streaming above, the endpoint is working! ✓"
echo ""
echo "Expected output format:"
echo "  data: {\"type\": \"chunk\", \"content\": \"...\"}"
echo "  event: done"
echo "  data: {\"finished\": true}"
echo ""
echo "Troubleshooting:"
echo "  - If no output: Check backend logs (docker logs virtualasistant_backend)"
echo "  - If 401 Unauthorized: Update TOKEN in this script"
echo "  - If 502 Bad Gateway: Check Nginx config"
echo "  - If buffered (all at once): Check Nginx proxy_buffering setting"
echo ""
echo "Next steps:"
echo "  1. Test in browser: http://localhost/chat-stream"
echo "  2. Check DevTools → Network → chat/stream/ → Response"
echo "  3. Monitor logs: docker-compose logs -f backend nginx"
echo ""
















