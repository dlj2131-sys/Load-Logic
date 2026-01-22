import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

def parse_submissions(submissions_folder: str, output_file: str = "organized_submissions.json"):
    """
    Parse all JSON files in the submissions folder and organize them logically.
    
    Args:
        submissions_folder: Path to the folder containing submission files
        output_file: Name of the output file to create
    """
    submissions_path = Path(submissions_folder)
    
    if not submissions_path.exists():
        print(f"Error: Submissions folder '{submissions_folder}' not found.")
        return
    
    # Find all JSON files in the submissions folder (exclude output files)
    all_json_files = list(submissions_path.glob("*.json"))
    # Exclude the organized_submissions.json file if it exists
    json_files = [f for f in all_json_files if f.name != "organized_submissions.json"]
    
    if not json_files:
        print(f"No JSON files found in '{submissions_folder}'")
        return
    
    print(f"Found {len(json_files)} submission file(s)")
    
    # Parse all submissions
    all_submissions = []
    errors = []
    
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract timestamp from filename if available
            filename = json_file.stem
            timestamp = None
            if 'T' in filename:
                try:
                    # Try to extract timestamp from filename like "booking-2026-01-22T21-03-05-963Z"
                    timestamp_str = filename.split('booking-')[1] if 'booking-' in filename else filename
                    # Parse ISO format timestamp
                    timestamp = timestamp_str.replace('T', ' ').split('-')[0:3]
                    timestamp = '-'.join(timestamp)
                except:
                    pass
            
            # Add metadata
            submission = {
                "submission_id": filename,
                "file_name": json_file.name,
                "timestamp": timestamp or json_file.stat().st_mtime,
                "data": data
            }
            
            all_submissions.append(submission)
            print(f"  [OK] Parsed: {json_file.name}")
            
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing {json_file.name}: {str(e)}"
            errors.append(error_msg)
            print(f"  [ERROR] {error_msg}")
        except Exception as e:
            error_msg = f"Error reading {json_file.name}: {str(e)}"
            errors.append(error_msg)
            print(f"  [ERROR] {error_msg}")
    
    # Organize submissions by date (if available) or by submission order
    organized_data = {
        "summary": {
            "total_submissions": len(all_submissions),
            "parse_date": datetime.now().isoformat(),
            "errors": len(errors)
        },
        "submissions": all_submissions,
        "errors": errors
    }
    
    # Group by delivery date for better organization
    by_delivery_date = {}
    for submission in all_submissions:
        delivery_date = submission["data"].get("deliveryDate", "unspecified")
        if delivery_date not in by_delivery_date:
            by_delivery_date[delivery_date] = []
        by_delivery_date[delivery_date].append(submission)
    
    organized_data["by_delivery_date"] = by_delivery_date
    
    # Group by priority
    by_priority = {}
    for submission in all_submissions:
        priority = submission["data"].get("deliveryPriority", "unspecified")
        if priority not in by_priority:
            by_priority[priority] = []
        by_priority[priority].append(submission)
    
    organized_data["by_priority"] = by_priority
    
    # Write to output file (save in submissions folder)
    output_path = submissions_path / output_file
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(organized_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SUCCESS] Successfully organized {len(all_submissions)} submission(s)")
    print(f"[SUCCESS] Output saved to: {output_path}")
    
    if errors:
        print(f"\n[WARNING] {len(errors)} error(s) encountered (see output file for details)")
    
    return organized_data


def create_summary_report(organized_data: Dict[str, Any], output_file: str = "submissions_summary.txt", base_folder: str = None):
    """
    Create a human-readable summary report of all submissions.
    
    Args:
        organized_data: The organized data dictionary from parse_submissions
        output_file: Name of the summary report file
        base_folder: Base folder path for output (defaults to submissions folder parent)
    """
    if base_folder:
        submissions_path = Path(base_folder)
    else:
        # Try to get path from first submission
        first_sub = organized_data.get("submissions", [{}])[0]
        if first_sub and first_sub.get("file_name"):
            submissions_path = Path(first_sub["file_name"]).parent.parent
        else:
            submissions_path = Path(".")
    
    output_path = submissions_path / output_file
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SUBMISSIONS SUMMARY REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        summary = organized_data.get("summary", {})
        f.write(f"Total Submissions: {summary.get('total_submissions', 0)}\n")
        f.write(f"Report Generated: {summary.get('parse_date', 'N/A')}\n")
        f.write(f"Errors: {summary.get('errors', 0)}\n\n")
        
        # Summary by delivery date
        f.write("-" * 80 + "\n")
        f.write("SUBMISSIONS BY DELIVERY DATE\n")
        f.write("-" * 80 + "\n\n")
        
        by_delivery = organized_data.get("by_delivery_date", {})
        for date in sorted(by_delivery.keys()):
            f.write(f"\nDelivery Date: {date}\n")
            f.write(f"  Number of orders: {len(by_delivery[date])}\n")
            for sub in by_delivery[date]:
                data = sub["data"]
                f.write(f"  - {data.get('name', 'N/A')} | {data.get('fuelType', 'N/A')} | "
                       f"Qty: {data.get('orderQuantity', 'N/A')} | "
                       f"Priority: {data.get('deliveryPriority', 'N/A')}\n")
        
        # Summary by priority
        f.write("\n" + "-" * 80 + "\n")
        f.write("SUBMISSIONS BY PRIORITY\n")
        f.write("-" * 80 + "\n\n")
        
        by_priority = organized_data.get("by_priority", {})
        for priority in sorted(by_priority.keys()):
            f.write(f"\nPriority: {priority.upper()}\n")
            f.write(f"  Number of orders: {len(by_priority[priority])}\n")
            for sub in by_priority[priority]:
                data = sub["data"]
                f.write(f"  - {data.get('name', 'N/A')} | Delivery: {data.get('deliveryDate', 'N/A')} | "
                       f"Qty: {data.get('orderQuantity', 'N/A')}\n")
        
        # Detailed submission information
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED SUBMISSION INFORMATION\n")
        f.write("=" * 80 + "\n\n")
        
        for idx, submission in enumerate(organized_data.get("submissions", []), 1):
            data = submission["data"]
            f.write(f"\nSubmission #{idx}: {submission.get('submission_id', 'N/A')}\n")
            f.write("-" * 80 + "\n")
            f.write(f"File: {submission.get('file_name', 'N/A')}\n")
            f.write(f"Timestamp: {submission.get('timestamp', 'N/A')}\n\n")
            
            f.write("Customer Information:\n")
            f.write(f"  Name: {data.get('name', 'N/A')}\n")
            f.write(f"  Phone: {data.get('phone', 'N/A')}\n")
            f.write(f"  Email: {data.get('email', 'N/A')}\n")
            f.write(f"  Address: {data.get('address', 'N/A')}\n\n")
            
            f.write("Order Details:\n")
            f.write(f"  Fuel Type: {data.get('fuelType', 'N/A')}\n")
            f.write(f"  Heating Unit: {data.get('heatingUnit', 'N/A')}\n")
            f.write(f"  Tank Location: {data.get('tankLocation', 'N/A')}\n")
            f.write(f"  Access Instructions: {data.get('accessInstructions', 'N/A')}\n")
            f.write(f"  Tank Level: {data.get('tankLevel', 'N/A')}%\n")
            f.write(f"  Order Quantity: {data.get('orderQuantity', 'N/A')}\n")
            f.write(f"  Tank Empty: {data.get('tankEmpty', 'N/A')}\n\n")
            
            f.write("Delivery Information:\n")
            f.write(f"  Delivery Date: {data.get('deliveryDate', 'N/A')}\n")
            f.write(f"  Delivery Priority: {data.get('deliveryPriority', 'N/A')}\n")
            f.write(f"  Special Considerations: {data.get('specialConsiderations', 'N/A')}\n\n")
            
            f.write("Payment Information:\n")
            f.write(f"  Payment Method: {data.get('paymentMethod', 'N/A')}\n")
            f.write(f"  Payment Authorization: {data.get('paymentAuthorization', 'N/A')}\n")
            f.write("\n")
    
    print(f"[SUCCESS] Summary report saved to: {output_path}")


if __name__ == "__main__":
    # Default path - adjust if needed
    submissions_folder = r"submissions"
    
    # Parse all submissions
    organized_data = parse_submissions(submissions_folder)
    
    if organized_data:
        # Create a human-readable summary report
        # Save in the submissions folder
        create_summary_report(organized_data, base_folder=submissions_folder)
        
        print("\n" + "=" * 80)
        print("Processing complete!")
        print("=" * 80)
