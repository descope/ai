import {registerPaidTool} from '@stripe/agent-toolkit/modelcontextprotocol';
import {z} from 'zod';

export const createServer = async (userEmail?: string) => {
  const { McpServer } = await import('@modelcontextprotocol/sdk/server/mcp.js');
  
  // Create server instance without trying to set capabilities directly
  const server = new McpServer({
    name: 'stripe-mcp-server',
    version: '0.1.0',
  });
  
  // Use registerPaidTool to add the paid functionality
  try {
    const coffeeRecommendations = {
      espresso: [
        "Try a double shot of Ethiopian Yirgacheffe for bright, floral notes",
        "Brazilian Santos beans create a smooth, chocolatey espresso",
        "Colombian Supremo offers balanced acidity with nutty undertones"
      ],
      pourover: [
        "Kenyan AA beans shine in pour-over with wine-like acidity",
        "Try a light roast Guatemalan Antigua for complex fruit flavors",
        "Costa Rican Tarrazú beans offer bright citrus notes in pour-over"
      ],
      coldBrew: [
        "Mexican Chiapas beans create a smooth, low-acid cold brew",
        "Try a coarse grind of Sumatra Mandheling for earthy cold brew",
        "Brazilian Cerrado beans make excellent chocolatey cold brew"
      ],
      french: [
        "Dark roast French Roast beans are perfect for French press",
        "Try a medium-dark Colombian for rich, full-bodied French press",
        "Sumatra beans create an earthy, bold French press coffee"
      ]
    };

    registerPaidTool(
      server as any,
      'get_premium_coffee_advice',
      'Get premium coffee recommendations and brewing tips from our coffee experts',
              {
          brewMethod: z.enum(['espresso', 'pourover', 'coldBrew', 'french']).describe('Your preferred brewing method (espresso, pourover, coldBrew, or french)'),
          intensity: z.enum(['light', 'medium', 'dark']).default('medium').describe('Preferred coffee intensity (light, medium, or dark)'),
        },
      ({brewMethod, intensity}: {brewMethod: string, intensity: string}) => {
        const recommendations = coffeeRecommendations[brewMethod as keyof typeof coffeeRecommendations];
        const randomRec = recommendations[Math.floor(Math.random() * recommendations.length)];
        
        const brewingTips = {
          espresso: "☕ Pro tip: Use 18-20g of coffee for a double shot, aim for 25-30 second extraction",
          pourover: "☕ Pro tip: Use a 1:15 ratio, bloom for 30 seconds, pour in slow circular motions",
          coldBrew: "☕ Pro tip: Steep for 12-24 hours, use a 1:4 ratio, strain twice for clarity",
          french: "☕ Pro tip: Use coarse grind, 4-minute steep time, press slowly and steadily"
        };

        return {
          content: [{
            type: 'text', 
            text: `☕ Premium Coffee Recommendation (${intensity} intensity):\n\n${randomRec}\n\n${brewingTips[brewMethod as keyof typeof brewingTips]}`
          }],
        };
      },
      {
        paymentReason: 'Premium coffee expertise requires a subscription! Support our coffee connoisseurs! ☕',
        stripeSecretKey: process.env.STRIPE_SECRET_KEY || '',
        userEmail: userEmail || 'user@example.com',
        checkout: {
          success_url: process.env.SUCCESS_URL || 'http://localhost:3000/success',
          line_items: [
            {
              price: process.env.STRIPE_PRICE_ID || '',
              quantity: 1,
            },
          ],
          mode: 'subscription',
        }
      }
    );
    console.log('Premium coffee advice tool registered successfully');
  } catch (error) {
    console.error('Failed to register premium coffee tool:', error);
    // Continue without the paid tool if registration fails
  }

  return { server };
};