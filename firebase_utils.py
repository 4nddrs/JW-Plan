import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Nueva función para obtener un solo documento por ID y colección
def get_record_by_id(collection_name, doc_id):
    doc_ref = db.collection(collection_name).document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def resolve_event_references(events):
    # Crear cachés para evitar múltiples lecturas de la base de datos
    locations_cache = {}
    conductors_cache = {}
    territories_cache = {}
    
    for event in events:
        # Resolver Location
        if 'location' in event and isinstance(event['location'], firestore.DocumentReference):
            loc_id = event['location'].id
            if loc_id not in locations_cache:
                loc_data = get_record_by_id('locations', loc_id)
                locations_cache[loc_id] = loc_data['name'] if loc_data and 'name' in loc_data else 'Unknown Location'
            event['location_name'] = locations_cache[loc_id]

        # Resolver Conductor
        if 'conductor' in event and isinstance(event['conductor'], firestore.DocumentReference):
            con_id = event['conductor'].id
            if con_id not in conductors_cache:
                con_data = get_record_by_id('conductors', con_id)
                conductors_cache[con_id] = con_data['name'] if con_data and 'name' in con_data else 'Unknown Conductor'
            event['conductor_name'] = conductors_cache[con_id]
        
        # Resolver Territory
        if 'territory' in event and isinstance(event['territory'], firestore.DocumentReference):
            ter_id = event['territory'].id
            if ter_id not in territories_cache:
                ter_data = get_record_by_id('territories', ter_id)
                territories_cache[ter_id] = ter_data['number'] if ter_data and 'number' in ter_data else 'N/A'
            event['territory_number'] = territories_cache[ter_id]

    return events

# Firestore utility functions
def get_all(collection_name):
    """Return all documents from a collection as a list of dicts with id"""
    docs = db.collection(collection_name).stream()
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        result.append(data)
    return result


def add_record(collection_name, data):
    """Add a new document to a collection"""
    db.collection(collection_name).add(data)


def delete_record(collection_name, doc_id):
    """Delete a document by id"""
    db.collection(collection_name).document(doc_id).delete()
