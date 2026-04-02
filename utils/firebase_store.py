import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables from .env
load_dotenv()

import json

def seed_firebase_promotions():
    """Seed the Firestore database with initial dummy retail promotions."""
    if not firebase_admin._apps:
        # First try to load from a raw environment string (like in cloud environments)
        firebase_secret = os.environ.get("FIREBASE_JSON_STRING")
        if firebase_secret:
            try:
                cred_dict = json.loads(firebase_secret)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                print(f"Failed to parse FIREBASE_JSON_STRING: {e}")
        else:
            # Fallback to physical .json file loaded from .env
            cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
            if not cred_path or not os.path.exists(cred_path):
                print(f"Error: FIREBASE_CREDENTIALS_PATH '{cred_path}' is invalid or file not found.")
                print("Please provide a valid file OR set FIREBASE_JSON_STRING in your environment variables.")
                return
                
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        
    db = firestore.client()
    
    promotions = [
        {"location": "new york", "details": "Buy one get one free on all winter apparel at the New York branch."},
        {"location": "san francisco", "details": "20% off all tech accessories this weekend only!"},
        {"location": "seattle", "details": "Free umbrella with any purchase over $50!"},
        {"location": "online", "details": "10% off site-wide on all online orders with code RETAIL10."}
    ]
    
    col_ref = db.collection("promotions")
    
    print("Upserting promotions into Firestore...")
    for promo in promotions:
        # Use location as a safe document ID
        doc_id = promo["location"].replace(" ", "_")
        col_ref.document(doc_id).set(promo)
        print(f" - Added promo for: {promo['location']}")
        
    print("Firebase promotions seeded successfully!")

if __name__ == "__main__":
    seed_firebase_promotions()
