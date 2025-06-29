import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import dotenv from 'dotenv';
dotenv.config();

const APP_ID = process.env.NUTRIONIX_APP_ID!;
const APP_KEY = process.env.NUTRIONIX_APP_KEY!;
const BASE_API_URL = 'https://trackapi.nutritionix.com';
const NUTRION_API_URL = `${BASE_API_URL}/v2/natural/nutrients`;
const EXERCISE_API_URL = `${BASE_API_URL}/v2/natural/exercise`;

interface NutritionixFood {
  food_name: string;
  serving_weight_grams: number;
  nf_calories: number;
  nf_protein: number;
  nf_total_fat: number;
  nf_total_carbohydrate: number;
}

interface NutritionixExercise {
  name: string;
  duration_min: number;
  nf_calories: number;
  description: string;
  benefits: string;
}

async function makeNutritionixRequest<T>(url: string, query: string, key: string): Promise<T[] | undefined> {
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-app-id': APP_ID,
        'x-app-key': APP_KEY,
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      console.error(`Error: ${response.status} - ${await response.text()}`);
      return undefined;
    }

    const data = await response.json();
    const items: T[] = data[key];

    return items;
  } catch (error) {
    console.error('Request failed:', error);
    return undefined;
  }
}

// Format nutrition data
function formatNutrition(food: NutritionixFood): string {
  return [
    `Your food is ${food.food_name.toUpperCase()}`,
    `The Serving Weight: ${food.serving_weight_grams}g`,
    `It contains calories: ${food.nf_calories} kcal`,
    `It contains protein: ${food.nf_protein} g`,
    `It contains fat: ${food.nf_total_fat} g`,
    `It contains carbohydrates: ${food.nf_total_carbohydrate} g`,
  ].join('\n');
}

// Format exercise data
function formatExercise(exercise: NutritionixExercise): string {
  return [
    `Your exercise is ${exercise.name}`,
    `The duration you performed your exercise: ${exercise.duration_min} minutes`,
    `You burnt approximately: ${exercise.nf_calories} calories`,
    `Here is a description of your exercise: ${exercise.description} g`,
    `Some of the benefits of your exercise are: ${exercise.benefits} g`,
  ].join('\n');
}

export const createServer = () => {
  // Create server instance
  const server = new McpServer({
    name: 'nutrition',
    version: '1.0.0',
  });

  // Register nutrition tool
  server.tool(
    'get-nutrition',
    'Get nutritional information about any meal, like calories, protein, carbohydrate and fat content.',
    {
      query: z.string().describe('Description of food/meal'),
    },
    async ({ query }) => {
      const nutritionalInfo: NutritionixFood[] | undefined =
        await makeNutritionixRequest<NutritionixFood>(NUTRION_API_URL, query, 'foods');

      if (!nutritionalInfo) {
        return {
          content: [
            {
              type: 'text',
              text: 'Failed to retrieve nutrition data',
            },
          ],
        };
      }

      if (nutritionalInfo.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: `No foods found for your query "${query}"`,
            },
          ],
        };
      }

      const formattedNutrition = nutritionalInfo.map(formatNutrition);
      const nutritionText = `Nutrition in your meal:\n\n${formattedNutrition.join('\n')}`;

      return {
        content: [
          {
            type: 'text',
            text: nutritionText,
          },
        ],
      };
    }
  );

  // Register exercise tool
  server.tool(
    'get-exercise',
    'Get the approximate calories burnt performing an exercise/workout for a certain duration of time.',
    {
      query: z.string().describe('Description of the exercise/workout.'),
    },
    async ({ query }) => {
      const exerciseInfo: NutritionixExercise[] | undefined =
        await makeNutritionixRequest<NutritionixExercise>(EXERCISE_API_URL, query, 'exercises');

      if (!exerciseInfo) {
        return {
          content: [
            {
              type: 'text',
              text: 'Failed to retrieve exercise data',
            },
          ],
        };
      }

      if (exerciseInfo.length === 0) {
        return {
          content: [
            {
              type: 'text',
              text: `No exercises found for your query "${query}"`,
            },
          ],
        };
      }

      const formattedExercise = exerciseInfo.map(formatExercise);
      const exerciseText = `Calories in your Workouts:\n\n${formattedExercise.join('\n')}`;

      return {
        content: [
          {
            type: 'text',
            text: exerciseText,
          },
        ],
      };
    }
  );
  return { server };
};
