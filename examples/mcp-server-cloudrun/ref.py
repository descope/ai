import requests

# 🔐 Replace these with your actual Nutritionix credentials
APP_ID = "826391e7"
APP_KEY = "a6dd75efdc8c41409335899485f4fe37	"

# 🌮 The food input you'd like to analyze
query = "2 eggs and 200g chicken breast"

url = "https://trackapi.nutritionix.com/v2/natural/nutrients"

headers = {
    "Content-Type": "application/json",
    "x-app-id": APP_ID,
    "x-app-key": APP_KEY,
}

data = {
    "query": query
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    nutrition_data = response.json()
    for food in nutrition_data['foods']:
        print(f"\n🍽️ {food['food_name'].title()}")
        print(f"  Serving weight: {food['serving_weight_grams']}g")
        print(f"  Calories: {food['nf_calories']} kcal")
        print(f"  Protein: {food['nf_protein']} g")
        print(f"  Fat: {food['nf_total_fat']} g")
        print(f"  Carbs: {food['nf_total_carbohydrate']} g")
else:
    print(f"❌ Failed to fetch data: {response.status_code} - {response.text}")