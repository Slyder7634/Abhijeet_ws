"""
Challan Generator - Flask Backend Server
Handles MongoDB storage (with JSON fallback), PDF generation, live previews, and CSV exports.
"""

import os
import json
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import csv
from io import StringIO, BytesIO
from typing import List, Dict, Any

from app import get_generator

app = Flask(__name__)
CORS(app)

# MongoDB Connection Setup
MONGODB_URI = "mongodb://localhost:27017"
DB_NAME = "challan_generator"
COLLECTION_NAME = "submissions"

use_mongo = False
collection = None

try:
    from pymongo import MongoClient, DESCENDING
    from bson import ObjectId
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1500)
    client.server_info()
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    if COLLECTION_NAME not in db.list_collection_names():
        db.create_collection(COLLECTION_NAME)
    use_mongo = True
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"⚠️ MongoDB connection failed ({e}). Falling back to local JSON storage.")
    use_mongo = False

# Local JSON Storage Fallback
JSON_STORAGE_PATH = os.path.join(os.path.dirname(__file__), 'submissions.json')

def load_local_submissions() -> List[Dict]:
    if not os.path.exists(JSON_STORAGE_PATH):
        return []
    try:
        with open(JSON_STORAGE_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_local_submissions(submissions: List[Dict]):
    with open(JSON_STORAGE_PATH, 'w') as f:
        json.dump(submissions, f, indent=4)

generator = get_generator()


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "storage": "mongodb" if use_mongo else "json"
    })


@app.route('/api/submit', methods=['POST'])
def submit():
    try:
        data = request.json or {}
        
        # Check basic fields
        name = data.get('studentName', data.get('customerName', ''))
        roll = data.get('rollNo', data.get('challanNumber', ''))
        
        if not name and not roll:
            return jsonify({"error": "Student / Customer Name or Roll / Challan Number is required"}), 400

        # Generate enriched data & PDF
        enriched_data = generator.process_data_and_totals(data)
        pdf_bytes = generator.generate_challan(enriched_data)
        
        roll_id = enriched_data.get('rollNo', 'challan')
        filename = f"Challan_{roll_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        save_path = os.path.join(generator.base_dir, 'generated', filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'wb') as f:
            f.write(pdf_bytes)
            
        sub_id = f"sub_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        submission = {
            "_id": sub_id,
            "studentName": enriched_data.get('studentName', 'Customer'),
            "rollNo": enriched_data.get('rollNo', '001'),
            "amount": enriched_data.get('amount', '0.00'),
            "description": enriched_data.get('description', 'Services'),
            "date": enriched_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            "pdfFilename": filename,
            "createdAt": datetime.now().isoformat(),
            "status": "completed",
            "fullData": enriched_data
        }
        
        if use_mongo and collection is not None:
            db_sub = copy.deepcopy(submission)
            del db_sub['_id']
            res = collection.insert_one(db_sub)
            submission['_id'] = str(res.inserted_id)
        else:
            subs = load_local_submissions()
            subs.insert(0, submission)
            save_local_submissions(subs)
            
        submission['pdfUrl'] = f"/api/pdf/{filename}"
        
        return jsonify({
            "success": True,
            "message": "Challan generated successfully",
            "submission": submission
        })
        
    except Exception as e:
        print(f"Error submitting challan: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/submissions', methods=['GET'])
def get_submissions():
    try:
        submissions = []
        if use_mongo and collection is not None:
            raw_subs = list(collection.find({}).sort("createdAt", -1).limit(50))
            for sub in raw_subs:
                sub['_id'] = str(sub['_id'])
                sub['pdfUrl'] = f"/api/pdf/{sub.get('pdfFilename', '')}"
                submissions.append(sub)
            total_count = collection.count_documents({})
        else:
            submissions = load_local_submissions()
            total_count = len(submissions)
            for sub in submissions:
                sub['pdfUrl'] = f"/api/pdf/{sub.get('pdfFilename', '')}"
                
        return jsonify({
            "success": True,
            "count": len(submissions),
            "total": total_count,
            "submissions": submissions
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/submissions/<submission_id>', methods=['DELETE'])
def delete_submission(submission_id):
    try:
        filename_to_del = None
        
        if use_mongo and collection is not None:
            if ObjectId.is_valid(submission_id):
                sub = collection.find_one({"_id": ObjectId(submission_id)})
                if sub:
                    filename_to_del = sub.get('pdfFilename')
                    collection.delete_one({"_id": ObjectId(submission_id)})
        else:
            subs = load_local_submissions()
            new_subs = []
            for sub in subs:
                if str(sub.get('_id')) == str(submission_id):
                    filename_to_del = sub.get('pdfFilename')
                else:
                    new_subs.append(sub)
            save_local_submissions(new_subs)
            
        if filename_to_del:
            pdf_path = os.path.join(generator.base_dir, 'generated', filename_to_del)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                
        return jsonify({"success": True, "message": "Submission deleted"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export-csv', methods=['GET'])
def export_csv():
    try:
        if use_mongo and collection is not None:
            submissions = list(collection.find({}).sort("createdAt", -1))
        else:
            submissions = load_local_submissions()
            
        if not submissions:
            return jsonify({"error": "No submissions to export"}), 400
            
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Customer / Student Name', 'Roll / Challan No', 'Amount',
            'Description', 'Date', 'PDF File', 'Created At'
        ])
        
        for sub in submissions:
            writer.writerow([
                sub.get('studentName', ''),
                sub.get('rollNo', ''),
                sub.get('amount', ''),
                sub.get('description', ''),
                sub.get('date', ''),
                sub.get('pdfFilename', ''),
                sub.get('createdAt', '')
            ])
            
        output.seek(0)
        
        return send_file(
            BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pdf/<filename>', methods=['GET'])
def get_pdf(filename):
    try:
        pdf_path = os.path.join(generator.base_dir, 'generated', filename)
        if not os.path.exists(pdf_path):
            return jsonify({"error": "PDF not found"}), 404
        return send_file(pdf_path, mimetype='application/pdf')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    try:
        with open(generator.config_path, 'r') as f:
            config = json.load(f)
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/config', methods=['PUT'])
def update_config():
    try:
        new_config = request.json
        if not new_config:
            return jsonify({"error": "Invalid JSON configuration"}), 400
            
        generator.save_config(new_config)
        return jsonify({"success": True, "message": "Configuration updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/preview', methods=['POST'])
def generate_preview():
    """Generates PNG preview image bytes for instant Visual Designer preview"""
    try:
        payload = request.json or {}
        template_config = payload.get('config', generator.config)
        sample_data = payload.get('data', {
            'studentName': 'GSC GLASS PRIVATE LIMITED',
            'rollNo': '2026-2027/05',
            'amount': '84795.00',
            'description': 'RIGHT ANGLE SPM & ROLLER CONVEYOR',
            'date': '11-06-2026'
        })
        
        png_bytes = generator.render_preview_png(sample_data, template_config, dpi=150)
        return Response(png_bytes, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/templates', methods=['GET'])
def list_templates():
    try:
        templates_dir = os.path.join(generator.base_dir, 'templates')
        files = [f for f in os.listdir(templates_dir) if f.endswith('.pdf') or f.endswith('.png') or f.endswith('.jpg')]
        if os.path.exists(os.path.join(generator.base_dir, 'challan copy.pdf')):
            files.append('challan copy.pdf')
        return jsonify({"success": True, "templates": list(set(files))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("\n🚀 Starting Challan Backend Server on http://localhost:5173")
    app.run(host='0.0.0.0', port=5173, debug=True)