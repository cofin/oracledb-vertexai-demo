# 🎭 Live Demo Scenarios: See AI in Action

## Demo Setup Checklist

Before demonstrating, ensure:
- [ ] System is running: `uv run app health-check`
- [ ] Demo mode enabled: `uv run app demo enable`
- [ ] Cache is warm: `uv run app cache warm-demo`
- [ ] Fallback ready: `uv run app demo test-fallback`

## Scenario 1: The Coffee Novice (5 minutes)

**Persona**: Sarah, new to specialty coffee

### Demo Flow

**You**: "Let me show you how our AI helps customers discover coffee they'll love."

**Type**: "I don't know much about coffee but I want something sweet and not too strong"

**AI Response**:
```
I understand you're looking for a gentle introduction to specialty coffee!
For someone who prefers sweet and mild flavors, I recommend:

1. **Vanilla Caramel Latte** - Our house blend with vanilla and caramel,
   perfectly balanced and not overwhelming

2. **Colombian Supremo** - A medium roast with natural chocolate notes
   and a smooth, sweet finish

Both are available at our downtown location (shown on the map).
```

**Key Points to Highlight**:
- No keywords needed - understood "not too strong" = mild
- Personalized explanation for beginners
- Automatic location integration

### Metrics to Show
```
Search Time: 42ms
Confidence: 94%
Intent: PRODUCT_RECOMMENDATION
Products Found: 2
```

## Scenario 2: The Coffee Expert (5 minutes)

**Persona**: Dr. Chen, coffee connoisseur

### Demo Flow

**Type**: "I'm looking for a natural process Ethiopian with bright acidity and fruit-forward notes, preferably from Yirgacheffe region"

**AI Response**:
```
Excellent choice! For a sophisticated palate seeking Ethiopian naturals:

**Ethiopian Yirgacheffe Natural** - Gedeb Station
- Processing: Natural, sun-dried on raised beds
- Notes: Blueberry, wine-like, bergamot
- Acidity: Bright, citric
- Harvest: December 2023
- Altitude: 1,950-2,200 masl

We have 12 bags in stock at our Specialty Bar location.
Would you like me to reserve some for cupping?
```

**Key Points**:
- Handles complex, technical queries
- Provides expert-level details
- Real-time inventory integration

## Scenario 3: Problem Solving (5 minutes)

**Persona**: Mark, has dietary restrictions

### Demo Flow

**Type**: "I'm lactose intolerant and sensitive to caffeine. What can I drink?"

**AI Response**:
```
I can help you find delicious options that work with your dietary needs:

☕ **Low-Caffeine Options**:
- Swiss Water Decaf Colombian (99.9% caffeine-free)
- Half-caff House Blend (50% less caffeine)

🥛 **Dairy-Free Preparations**:
- Oat Milk Latte (creamy, naturally sweet)
- Almond Milk Cappuccino (light, nutty flavor)
- Coconut Milk Mocha (rich, tropical notes)

💡 **My Recommendation**: Try our Decaf Colombian with oat milk -
it's smooth, chocolatey, and many customers say it's better than regular!
```

**Key Points**:
- Understands health constraints
- Offers practical alternatives
- Empathetic, helpful tone

## Scenario 4: Location-Based (3 minutes)

### Demo Flow

**Type**: "Where can I get an espresso near the financial district before 7am?"

**AI Response**:
```
Early bird! Here are shops open before 7am near the financial district:

📍 **Main Street Café** (0.3 miles)
   Opens: 6:00 AM
   ⭐ Features: Express counter, mobile ordering

📍 **Corner Coffee Co** (0.5 miles)
   Opens: 5:30 AM
   ⭐ Features: Drive-through, breakfast menu

Both serve our signature espresso blend. Main Street is closer
but Corner Coffee opens earlier if you need the extra time!
```

**Show on map**: Pins appear showing exact locations

## Scenario 5: Natural Conversation (3 minutes)

### Demo Flow

**Conversation 1**:
- User: "Hello!"
- AI: "Hello! Welcome to our coffee assistant. What can I help you find today?"

**Conversation 2**:
- User: "I'm tired"
- AI: "Sounds like you could use an energy boost! Our Ethiopian Sidamo or a classic Espresso would help wake you up. What's your usual go-to when you need energy?"

**Conversation 3**:
- User: "Thanks, that was helpful!"
- AI: "You're very welcome! Enjoy your coffee, and feel free to ask if you need anything else! ☕"

**Key Points**:
- Natural, context-aware responses
- Maintains conversation flow
- Appropriate tone for each situation

## Scenario 6: Error Handling (2 minutes)

### Demo Flow

**Type**: "qwerty123 coffee xyz"

**AI Response**:
```
I'm not quite sure what you're looking for. Could you tell me more about:
- What kind of coffee flavors you enjoy?
- Whether you're looking for a specific drink?
- If you need help finding a location?

I'm here to help you find the perfect coffee!
```

**Disable network** (to show offline mode):
```
I'm currently in offline mode but I can still help!

Our popular choices include:
- House Blend: Balanced and smooth
- Dark Roast: Bold and intense
- Blonde Roast: Light and bright

All available at our 10 locations citywide!
```

## Performance Showcase (2 minutes)

### Live Metrics Dashboard

Show the real-time dashboard:
```
Current Performance (Last Hour):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Queries Processed: 1,247
Average Response: 47ms
Cache Hit Rate: 89%
User Satisfaction: 94%
Cost per Query: $0.003
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Speed Test

Run several queries in quick succession:
1. "Espresso" → 32ms
2. "Sweet coffee" → 41ms
3. "Near me" → 38ms
4. "Organic options" → 45ms

**Average: 39ms** (Faster than Google Search!)

## Persona Quick-Select

For rapid demos, use these pre-configured personas:

```bash
# Coffee Novice
uv run app demo persona --name=sarah
# Preset queries loaded for beginner perspective

# Coffee Expert
uv run app demo persona --name=dr-chen
# Technical queries ready

# Health Conscious
uv run app demo persona --name=mark
# Dietary restriction queries

# Busy Professional
uv run app demo persona --name=alex
# Location and speed focused
```

## Demo Tips

### Do's ✅
- Start with simple queries, build complexity
- Show the map integration early
- Highlight speed with live metrics
- Mention cost savings vs traditional search
- Let audience try their own queries

### Don'ts ❌
- Don't use technical jargon initially
- Don't skip the "wow" moments (speed, understanding)
- Don't forget to show fallback capability
- Don't rush - let the AI magic sink in

## Common Audience Questions

**Q: "How accurate is it?"**
A: "95% intent detection accuracy, validated on 10,000+ real queries"

**Q: "What if it doesn't understand?"**
A: *Show fallback demo* "Multiple safety nets ensure great experience"

**Q: "How much does this cost?"**
A: "Average $0.003 per query - 10x cheaper than human support"

**Q: "Can it learn our specific products?"**
A: "Yes! It learns from your catalog and can be customized"

**Q: "What about different languages?"**
A: "Gemini supports 100+ languages out of the box"

## Conference/Trade Show Mode

### Quick Demo (30 seconds)
1. "I want something smooth" → Instant results
2. Show speed metrics
3. "Find a shop near the convention center" → Map pins
4. Hand business card

### Full Demo (5 minutes)
1. Novice scenario
2. Expert scenario
3. Performance metrics
4. ROI discussion
5. Q&A

### Booth Attractor Mode
```bash
# Run continuous demo
uv run app demo attract-mode

# Cycles through impressive queries automatically
# Shows live metrics and animations
# Resets every 2 minutes
```

## Post-Demo Resources

### For Technical Audience
"Here's our implementation guide and architecture documentation..."
- Point to: [Implementation Guide](06-implementation-guide.md)

### For Business Audience
"Let me share our ROI calculator and case studies..."
- Point to: [Business Value](02-business-value.md)

### For Everyone
"Try it yourself at demo.coffeai.example.com"
- QR code with pre-loaded queries

## Troubleshooting Demo Issues

### If System is Slow
```bash
# Quick fix
uv run app cache clear-partial
uv run app demo boost-mode
```

### If AI Returns Errors
```bash
# Enable fallback
uv run app demo fallback-only
```

### If Nothing Works
"Let me show you a recorded demo of our peak performance..."
- Have video backup ready!

---

*"The best demos don't feel like demos - they feel like magic that solves real problems."* - Sales Engineering Lead
