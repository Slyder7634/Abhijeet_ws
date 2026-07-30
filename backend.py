"""
Challan Generator - Flask Backend Server
Handles MongoDB storage (with JSON fallback), PDF generation, live previews, and CSV exports.
"""

import os
import json
import copy
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

        # Generate enriched data, then produce two independent PDFs
        enriched_data = generator.process_data_and_totals(data)
        pdfs = generator.generate_dual_documents(enriched_data)

        # Get customer name for filename
        customer_name = enriched_data.get('studentName', enriched_data.get('customerName', 'Customer'))
        # Clean customer name for filename
        clean_name = "".join(c if c.isalnum() or c.isspace() else "_" for c in customer_name)
        clean_name = clean_name.replace(" ", "_")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        bill_filename = f"Bill_{clean_name}_{timestamp}.pdf"
        challan_filename = f"Challan_{clean_name}_{timestamp}.pdf"

        generated_dir = os.path.join(generator.base_dir, 'generated')
        os.makedirs(generated_dir, exist_ok=True)

        with open(os.path.join(generated_dir, bill_filename), 'wb') as f:
            f.write(pdfs['bill'])
        with open(os.path.join(generated_dir, challan_filename), 'wb') as f:
            f.write(pdfs['challan'])

        # Get vehicle numbers from data - challan and bill each have their own,
        # independently editable, vehicle number
        challan_vehicle_no = enriched_data.get('challan_vehicle_no', '')
        bill_vehicle_no = enriched_data.get('bill_vehicle_no', '')
        challan_number = enriched_data.get('challanNumber', f"CH-{datetime.now().strftime('%Y%m%d')}-001")
        
        sub_id = f"sub_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        submission = {
            "_id": sub_id,
            "studentName": customer_name,
            "rollNo": enriched_data.get('rollNo', '001'),
            "challanNumber": challan_number,
            "amount": enriched_data.get('amount', '0.00'),
            "description": enriched_data.get('description', 'Services'),
            "date": enriched_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            "challan_vehicle_no": challan_vehicle_no,
            "bill_vehicle_no": bill_vehicle_no,
            "vehicle_no": challan_vehicle_no,  # kept for backward compatibility with older UI/records
            "pdfFilename": bill_filename,
            "billFilename": bill_filename,
            "challanFilename": challan_filename,
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat(),
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
            
        submission['pdfUrl'] = f"/api/pdf/{bill_filename}"
        submission['billUrl'] = f"/api/pdf/{bill_filename}"
        submission['challanUrl'] = f"/api/pdf/{challan_filename}"
        
        return jsonify({
            "success": True,
            "message": "Bill and Challan generated successfully",
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


@app.route('/api/submissions/search', methods=['POST'])
def search_submissions():
    """Search submissions with filters"""
    try:
        search_data = request.json or {}
        search_type = search_data.get('search_type', '')
        query = search_data.get('query', '')
        
        if not use_mongo or collection is None:
            # Fallback to local search
            subs = load_local_submissions()
            filtered = []
            query_lower = query.lower()
            for sub in subs:
                if search_type == "Customer Name":
                    if query_lower in sub.get('studentName', '').lower():
                        filtered.append(sub)
                elif search_type == "Challan Number":
                    if query_lower in sub.get('challanNumber', '').lower():
                        filtered.append(sub)
                elif search_type == "GSTIN":
                    if query_lower in sub.get('fullData', {}).get('customer_gstin', '').lower():
                        filtered.append(sub)
                elif search_type == "Vehicle No":
                    haystack = " ".join([
                        sub.get('challan_vehicle_no', ''),
                        sub.get('bill_vehicle_no', ''),
                        sub.get('vehicle_no', '')
                    ]).lower()
                    if query_lower in haystack:
                        filtered.append(sub)
                else:
                    filtered.append(sub)
            return jsonify({
                "success": True,
                "count": len(filtered),
                "submissions": filtered[:100]
            })
        
        # Build search filter
        filter_query = {}
        
        if search_type == "Challan Number":
            filter_query['challanNumber'] = {"$regex": query, "$options": "i"}
        elif search_type == "Customer Name":
            filter_query['studentName'] = {"$regex": query, "$options": "i"}
        elif search_type == "Date Range":
            from_date = search_data.get('from_date')
            to_date = search_data.get('to_date')
            if from_date and to_date:
                filter_query['date'] = {"$gte": from_date, "$lte": to_date}
        elif search_type == "Amount Range":
            min_amt = float(search_data.get('min_amount', 0))
            max_amt = float(search_data.get('max_amount', 999999))
            filter_query['amount'] = {"$gte": str(min_amt), "$lte": str(max_amt)}
        elif search_type == "GSTIN":
            filter_query['fullData.customer_gstin'] = {"$regex": query, "$options": "i"}
        elif search_type == "Vehicle No":
            filter_query['$or'] = [
                {'challan_vehicle_no': {"$regex": query, "$options": "i"}},
                {'bill_vehicle_no': {"$regex": query, "$options": "i"}},
                {'vehicle_no': {"$regex": query, "$options": "i"}},
            ]
            
        # Get submissions
        submissions = list(collection.find(filter_query).sort("createdAt", -1).limit(100))
        for sub in submissions:
            sub['_id'] = str(sub['_id'])
            sub['pdfUrl'] = f"/api/pdf/{sub.get('pdfFilename', '')}"
            
        return jsonify({
            "success": True,
            "count": len(submissions),
            "submissions": submissions
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/submissions/recent', methods=['GET'])
def get_recent_submissions():
    """Get recent submissions"""
    try:
        limit = int(request.args.get('limit', 50))
        
        if use_mongo and collection is not None:
            submissions = list(collection.find({}).sort("createdAt", -1).limit(limit))
            for sub in submissions:
                sub['_id'] = str(sub['_id'])
                sub['pdfUrl'] = f"/api/pdf/{sub.get('pdfFilename', '')}"
                
            return jsonify({
                "success": True,
                "count": len(submissions),
                "submissions": submissions
            })
        else:
            subs = load_local_submissions()
            return jsonify({
                "success": True,
                "count": len(subs),
                "submissions": subs[:limit]
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/submissions/<submission_id>', methods=['GET'])
def get_submission(submission_id):
    """Fetch a single submission's full detail - used to pre-fill the edit form"""
    try:
        if use_mongo and collection is not None:
            sub = None
            if ObjectId.is_valid(submission_id):
                sub = collection.find_one({"_id": ObjectId(submission_id)})
            if not sub:
                return jsonify({"error": "Submission not found"}), 404
            sub['_id'] = str(sub['_id'])
        else:
            subs = load_local_submissions()
            sub = next((s for s in subs if str(s.get('_id')) == str(submission_id)), None)
            if not sub:
                return jsonify({"error": "Submission not found"}), 404

        return jsonify({"success": True, "submission": sub})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/submissions/<submission_id>', methods=['PUT'])
def update_submission(submission_id):
    """
    Edit an existing submission. Accepts the same shape of payload as /api/submit
    (full form data, including challan_vehicle_no / bill_vehicle_no), recalculates
    totals, regenerates BOTH the Bill and the Challan PDFs from the corrected data,
    and overwrites the original files in place so every link/reference to this
    submission stays valid - fixing a wrong vehicle number (or anything else) on
    one edit updates both documents at once.
    """
    try:
        data = request.json or {}

        # Locate the existing record so we know which files to overwrite and
        # can preserve immutable fields (id, createdAt).
        if use_mongo and collection is not None:
            if not ObjectId.is_valid(submission_id):
                return jsonify({"error": "Submission not found"}), 404
            existing = collection.find_one({"_id": ObjectId(submission_id)})
            if not existing:
                return jsonify({"error": "Submission not found"}), 404
        else:
            subs = load_local_submissions()
            existing = next((s for s in subs if str(s.get('_id')) == str(submission_id)), None)
            if not existing:
                return jsonify({"error": "Submission not found"}), 404

        name = data.get('studentName', data.get('customerName', existing.get('studentName', '')))
        roll = data.get('rollNo', data.get('challanNumber', existing.get('rollNo', '')))
        if not name and not roll:
            return jsonify({"error": "Student / Customer Name or Roll / Challan Number is required"}), 400

        enriched_data = generator.process_data_and_totals(data)
        pdfs = generator.generate_dual_documents(enriched_data)

        # Reuse the original filenames so every existing link/reference keeps working
        bill_filename = existing.get('billFilename') or existing.get('pdfFilename')
        challan_filename = existing.get('challanFilename')
        generated_dir = os.path.join(generator.base_dir, 'generated')
        os.makedirs(generated_dir, exist_ok=True)

        if not bill_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            bill_filename = f"Bill_{submission_id}_{timestamp}.pdf"
        if not challan_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            challan_filename = f"Challan_{submission_id}_{timestamp}.pdf"

        with open(os.path.join(generated_dir, bill_filename), 'wb') as f:
            f.write(pdfs['bill'])
        with open(os.path.join(generated_dir, challan_filename), 'wb') as f:
            f.write(pdfs['challan'])

        challan_vehicle_no = enriched_data.get('challan_vehicle_no', '')
        bill_vehicle_no = enriched_data.get('bill_vehicle_no', '')
        challan_number = enriched_data.get('challanNumber', existing.get('challanNumber', ''))

        updated_fields = {
            "studentName": name,
            "rollNo": enriched_data.get('rollNo', existing.get('rollNo', '001')),
            "challanNumber": challan_number,
            "amount": enriched_data.get('amount', '0.00'),
            "description": enriched_data.get('description', 'Services'),
            "date": enriched_data.get('date', existing.get('date', '')),
            "challan_vehicle_no": challan_vehicle_no,
            "bill_vehicle_no": bill_vehicle_no,
            "vehicle_no": challan_vehicle_no,
            "pdfFilename": bill_filename,
            "billFilename": bill_filename,
            "challanFilename": challan_filename,
            "updatedAt": datetime.now().isoformat(),
            "status": "completed",
            "fullData": enriched_data
        }

        if use_mongo and collection is not None:
            collection.update_one({"_id": ObjectId(submission_id)}, {"$set": updated_fields})
            updated = collection.find_one({"_id": ObjectId(submission_id)})
            updated['_id'] = str(updated['_id'])
        else:
            subs = load_local_submissions()
            updated = None
            for s in subs:
                if str(s.get('_id')) == str(submission_id):
                    s.update(updated_fields)
                    updated = s
                    break
            save_local_submissions(subs)

        updated['pdfUrl'] = f"/api/pdf/{bill_filename}"
        updated['billUrl'] = f"/api/pdf/{bill_filename}"
        updated['challanUrl'] = f"/api/pdf/{challan_filename}"

        return jsonify({
            "success": True,
            "message": "Submission updated - Bill and Challan regenerated",
            "submission": updated
        })

    except Exception as e:
        print(f"Error updating submission: {e}")
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
            'Customer / Student Name', 'Challan Number', 'Challan Vehicle No', 'Bill Vehicle No',
            'Amount', 'Description', 'Date', 'PDF File', 'Created At'
        ])
        
        for sub in submissions:
            writer.writerow([
                sub.get('studentName', ''),
                sub.get('challanNumber', ''),
                sub.get('challan_vehicle_no', sub.get('vehicle_no', '')),
                sub.get('bill_vehicle_no', sub.get('vehicle_no', '')),
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
        
        # Increased DPI for higher quality preview
        png_bytes = generator.render_preview_png(sample_data, template_config, dpi=200)
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