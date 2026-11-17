# Chatbot Implementation Guide

## Overview
The chatbot is now integrated with the `/api/product-agent` endpoint to provide intelligent product search and recommendations. When users ask questions about products, the chatbot fetches real product data and displays them in an attractive card format.

## Files Updated

### 1. Controller: `controllers/chatbot.py`
**Endpoint:** `/chatbot/message` (POST)

**Features:**
- Accepts user messages as JSON: `{ "message": "user query" }`
- Calls `/api/product-agent` API for product search
- Returns structured response with answer and products
- Implements fallback responses for graceful degradation
- Handles errors gracefully

**Response Format:**
```json
{
    "status": "success|error",
    "source": "web|chat",
    "answer": "Bot response text",
    "products": [
        {
            "name": "Product Name",
            "description": "Product details",
            "price": "Cost information",
            "image_url": "image link",
            "url": "product page link"
        }
    ]
}
```

### 2. Frontend: `static/src/js/chatbot.js`
**Key Methods:**
- `ChatbotWidget.sendToBackend()`: Sends user message to backend
- `displayProducts()`: Renders product cards in the chat
- `createProductCard()`: Creates individual product card HTML
- `sendMessage()`: Handles user input and UI updates

**Features:**
- Real-time message display
- Typing indicator while waiting for response
- Product card rendering with images, names, prices, and links
- Auto-scroll to latest messages
- Error handling and user feedback

### 3. Styles: `static/src/css/chatbot.css`
**Product Card Styling:**
 `.products-grid`: Layout container for products
 `.product-card`: Individual product card with hover effects
 `.product-image`: Image display with fallback
 `.product-name`: Title with 2-line text truncation
 `.product-description`: Description with ellipsis
 `.product-price`: Highlighted price display
 `.product-link`: "View Details" button with gradient

## How It Works

### Step 1: User Asks a Question
```
User: "Show me laptops"
```

### Step 2: Frontend Sends to Backend
```
POST /chatbot/message
Content-Type: application/json
Body: { "message": "Show me laptops" }
```

### Step 3: Backend Calls Product Agent
```
POST /api/product-agent
Body: { "query": "Show me laptops" }
```

### Step 4: Product Agent Returns Results
```json
{
    "status": "success",
    "source": "web",
    "answer": "Here are some laptops I found for you 🔍",
    "products": [
        {
            "name": "Dell XPS 13",
            "description": "Powerful ultrabook...",
            "price": "$999",
            "image_url": "...",
            "url": "..."
        }
    ]
}
```

### Step 5: Frontend Displays Results
- Shows answer text
- Displays up to 3 product cards
- Each card is clickable and links to product page

## Testing the Chatbot

### Test Cases

1. **Product Search:**
   ```
   Q: "I need a laptop"
   Expected: Shows laptop products
   ```

2. **Greeting:**
   ```
   Q: "Hello"
   Expected: Greeting response without products
   ```

3. **Order Status:**
   ```
   Q: "Track my order"
   Expected: Order tracking instructions
   ```

4. **Fallback (when API unavailable):**
   ```
   Q: "Any product query"
   Expected: Fallback response with helpful message
   ```

## API Integration

### Product Agent Endpoint
**URL:** `/api/product-agent`  
**Method:** POST  
**Auth:** public  
**CSRF:** Disabled  

**Request:**
```json
{
    "query": "user question about products"
}
```

**Response:**
```json
{
    "status": "success",
    "source": "web",
    "answer": "Response message",
    "products": [...]
}
```

## Customization

### Change Chat Icon
Edit `chatbot_template.xml`:
```xml
<span class="chat-icon">💬</span>  <!-- Change emoji -->
```

### Change Colors
Edit `chatbot.css`:
```css
.chat-toggle-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);  /* Change colors */
}
```

### Change Product Card Layout
Edit `chatbot.js` in `createProductCard()` method to modify card structure.

## Troubleshooting

### Issue: Products not showing
**Solution:** Check if `/api/product-agent` endpoint is running and returning data.

### Issue: Images not loading
**Solution:** Ensure `image_url` is provided in product response. Fallback SVG is used if missing.

### Issue: Chat not opening
**Solution:** Check browser console for JavaScript errors. Ensure `chatbot.js` and `chatbot.css` are loaded.

### Issue: CSRF token errors
**Solution:** The endpoint has `csrf=False`. If needed, get token from Odoo's security headers.

## Files Structure
```
chatbot/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── chatbot.py          # ✓ Updated
├── models/
├── security/
├── static/
│   └── src/
│       ├── css/
│       │   └── chatbot.css  # ✓ Updated
│       └── js/
│           └── chatbot.js   # ✓ Updated
└── views/
    └── chatbot_template.xml
```

## Performance Notes

- Typing indicator shows while waiting for product agent response
- Products limited to first 3 results for chat UI
- Images lazy-load with fallback SVG
- Chat window has smooth animations
- Responsive design for mobile devices

## Dependencies

- Requires `/api/product-agent` endpoint from Xevoria_electronics module
- Requires `requests` library for backend API calls
- Frontend uses vanilla JavaScript (no external dependencies)

## Next Steps

1. Test with real product data
2. Customize colors and styling to match brand
3. Add more fallback responses as needed
4. Monitor performance with heavy traffic
5. Add analytics to track user interactions
