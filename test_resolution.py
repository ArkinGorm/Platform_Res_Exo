import requests
import time
import json

BASE_URL = "http://localhost:8000/api"

def test_full_flow():
    print("._. Test du flux complet d'exécution...")
    
    # 1. Connexion
    print("\n1️⃣ Connexion...")
    login_data = {
        "email": "anak@test.com",
        "password": "Anak1@.$"
    }
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    token = response.json().get('access')
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Connecté")
    
    # 2. Récupérer les exercices
    print("\n2️⃣ Récupération des exercices...")
    response = requests.get(f"{BASE_URL}/exercises/published/", headers=headers)
    exercises = response.json()
    print(f"✅ {len(exercises)} exercices trouvés")
    
    if exercises:
        ex_id = exercises[0]['id']
        
        # 3. Soumettre une solution correcte
        print("\n3️⃣ Soumission d'une solution correcte...")
        submit_data = {
            "exercise": ex_id,
            "code": "function solution(a, b) { return a + b; }"
        }
        response = requests.post(f"{BASE_URL}/submissions/submit/", 
                               json=submit_data, headers=headers)
        result = response.json()
        submission_id = result['submission_id']
        print(f"✅ Soumission créée (ID: {submission_id})")
        
        # 4. Attendre l'exécution
        print("\n4️⃣ Attente de l'exécution...")
        for _ in range(10):
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/submissions/{submission_id}/", 
                                   headers=headers)
            status = response.json().get('status')
            print(f"   Statut: {status}")
            if status in ['passed', 'failed', 'error']:
                break
        
        # 5. Afficher les résultats
        print(f"\n5️⃣ Résultat final: {status}")
        if status == 'passed':
            print("✅ Tous les tests sont passés !")
        else:
            print("❌ Des tests ont échoué")
            
            # Voir les détails
            response = requests.get(f"{BASE_URL}/submissions/{submission_id}/", 
                                   headers=headers)
            submission = response.json()
            print("\nDétails des tests:")
            for result in submission.get('test_results', []):
                mark = "✅" if result['passed'] else "❌"
                print(f"  {mark} {result['test_case']}: {result.get('actual_output', '')}")

if __name__ == "__main__":
    test_full_flow()