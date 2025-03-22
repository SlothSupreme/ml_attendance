import argparse
import os
import requests
import csv
from datetime import datetime
from PIL import Image
import re  # Import the regular expression module

def convert_image(image_path, output_format="jpg"):
    """
    Converts an image to the specified format (jpg or png).
    Handles potential HEIC files.

    Args:
        image_path: Path to the input image.
        output_format: Desired output format ("jpg" or "png").  Defaults to "jpg".

    Returns:
        The path to the converted image, or None if conversion failed.
    """
    try:
        img = Image.open(image_path)
        base, ext = os.path.splitext(image_path)
        new_path = f"{base}.{output_format.lower()}"

        if ext.lower() == ".heic":
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener()  # Register HEIF opener (if library is installed)
                img = Image.open(image_path) #need to reopen
            except ImportError:
                print(f"Error: HEIC conversion requires pillow-heif.  Install with: pip install pillow-heif")
                return None

        if output_format.lower() == "jpg":
            img = img.convert("RGB")  # Convert to RGB for JPEG
            img.save(new_path, "JPEG")
        elif output_format.lower() == "png":
            img.save(new_path, "PNG")
        else:
            print(f"Error: Unsupported output format: {output_format}")
            return None

        os.remove(image_path) # remove the original
        return new_path
    except (FileNotFoundError, OSError) as e:
        print(f"Error converting image {image_path}: {e}")
        return None



def extract_url_parts(course_url):
    """
    Extracts the base URL and course ID from a Canvas course URL.

    Args:
        course_url: The full Canvas course URL.

    Returns:
        A tuple containing the base URL and course ID, or (None, None) on failure.
    """
    match = re.match(r"(https?://[^/]+)/courses/(\d+)", course_url)
    if match:
        base_url = match.group(1) + "/" #add the trailing slash
        course_id = int(match.group(2))  # Convert to integer
        return base_url, course_id
    else:
        return None, None


def download_submissions(api_key, base_url, course_id, assignment_id, output_path, convert_to=None):
    """
    Downloads student submissions for a Canvas assignment and generates a CSV.

    Args:
        api_key: Canvas API key.
        base_url: Base URL of the Canvas instance (e.g., "https://canvas.example.com/").
        course_id: The ID of the course.
        assignment_id: The ID of the assignment.
        output_path: Directory to save submissions and CSV.
        convert_to: Optional. If provided ('jpg' or 'png'), convert all images.

    Returns:
        None
    """

    # --- Basic Input Validation ---
    if not api_key or not base_url or not course_id or not assignment_id:
        raise ValueError("API key, base URL, course ID, and assignment ID are required.")
    if not base_url.startswith("https://"):
        raise ValueError("Base URL must start with 'https://'")
    if not isinstance(course_id, int):
        raise ValueError("Course ID must be an integer.")
    if not isinstance(assignment_id, int):
         raise ValueError("Assignment ID must be an integer")


    headers = {"Authorization": f"Bearer {api_key}"}
    assignment_url = f"{base_url}api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"  # Correct API endpoint
    params = {
        "include[]": ["user", "submission_comments"],  # Include user info and comments
        "per_page": 100  # Fetch up to 100 submissions (max allowed)
    }

    # Create Output Directory
    os.makedirs(output_path, exist_ok=True)  # Create directory if it doesn't exist

    # CSV
    csv_path = os.path.join(output_path, "submissions.csv")
    csv_file = open(csv_path, 'w', newline='', encoding='utf-8')  # Use utf-8 encoding
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        "Student Name", "Canvas ID", "Original Filename", "Renamed Filename",
        "Submission Date", "Submission Comment", "Late" , "Grade", "Excused"
    ])


    # Canvas Pagination
    while assignment_url:
        try:
            print(f"Requesting URL: {assignment_url}")  # Debug: URL
            response = requests.get(assignment_url, headers=headers, params=params)

            print(f"Status Code: {response.status_code}")  # Debug: Status

            if "Retry-After" in response.headers: # Debug rate limiting
                wait_time = int(response.headers["Retry-After"])
                print(f"Rate limited! Waiting {wait_time} seconds...")
                import time
                time.sleep(wait_time)
                continue # Go to the next iteration of the loop

            response.raise_for_status()  # Raise exception for bad status codes
            # print(f"Response Text: {response.text}")       # Debug: Raw Response

            submissions = response.json()


            for submission in submissions:
                # Extract Submission Data 
                user = submission.get("user", {})
                student_name = user.get("name", "Unknown")
                canvas_id = submission.get("user_id", "Unknown")
                submission_date_str = submission.get("submitted_at", None)  # Handle missing dates
                submission_date = datetime.strptime(submission_date_str, "%Y-%m-%dT%H:%M:%SZ") if submission_date_str else "No Submission"
                submission_comment = submission.get("submission_comments", [])
                submission_comment_text = "; ".join([comment.get("comment", "") for comment in submission_comment])
                late = submission.get("late", False)
                grade = submission.get("grade", None)
                excused = submission.get("excused", False)

                # Download attachments (if any)
                attachments = submission.get("attachments", [])
                for attachment in attachments:
                    try:
                        original_filename = attachment.get("filename")
                        download_url = attachment.get("url")

                        if not original_filename or not download_url:
                            print(f"Skipping attachment: Missing filename or URL in submission for student {canvas_id}")
                            continue

                        renamed_filename = f"{canvas_id}_{original_filename}"  # Basic renaming
                        file_path = os.path.join(output_path, renamed_filename)

                        # Download the file
                        download_response = requests.get(download_url, headers=headers, stream=True)
                        download_response.raise_for_status()

                        with open(file_path, 'wb') as file:
                            for chunk in download_response.iter_content(chunk_size=8192):
                                file.write(chunk)

                        # Image conversion
                        if convert_to:
                            converted_path = convert_image(file_path, convert_to)
                            if converted_path:
                                 renamed_filename = os.path.basename(converted_path)
                                 file_path = converted_path
                            else:
                                print(f"Conversion failed for {original_filename}. Keeping original.")

                        #write to csv
                        csv_writer.writerow([
                            student_name, canvas_id, original_filename,
                            renamed_filename, submission_date, submission_comment_text,
                            late, grade, excused
                        ])
                        print(f"Downloaded: {renamed_filename}")

                    except requests.exceptions.RequestException as e:
                        print(f"Error downloading attachment for student {canvas_id}: {e}")
                    except Exception as e:  # Catch any other errors during processing
                        print(f"Error processing attachment for student {canvas_id}: {e}")


            # --- Handle Pagination (check for 'next' link) ---
            links = response.headers.get('Link')
            assignment_url = None  # Assume no next page unless found
            if links:
                for link in links.split(','):
                    parts = link.split(';')
                    if len(parts) == 2 and 'rel="next"' in parts[1]:
                        assignment_url = parts[0].strip('<> ')
                        break  # Found the "next" URL, exit the inner loop


        except requests.exceptions.RequestException as e:
            print(f"Error fetching submissions: {e}")
            break  # Exit the outer loop on a request error
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break
    csv_file.close()
    print("Download and CSV creation complete.")



def main():
    parser = argparse.ArgumentParser(description="Download Canvas assignment submissions.")
    parser.add_argument("--assignment", required=True, type=int, help="Canvas assignment number")
    parser.add_argument("--output", help="Output directory (defaults to ./<assignment_id>)")
    parser.add_argument("--convert", choices=['jpg', 'png'], help="Convert images to specified format")

    args = parser.parse_args()

    # Load API key and course URL from environment variables
    api_key = os.environ.get("CANVAS_API_KEY")
    course_url = os.environ.get("CANVAS_COURSE_URL")

    if not api_key or not course_url:
        print("Error: CANVAS_API_KEY and CANVAS_COURSE_URL environment variables must be set.")
        return

    # Extract base URL and course ID
    base_url, course_id = extract_url_parts(course_url)
    if not base_url or not course_id:
        print("Error: Invalid course URL format.  Must be like https://canvas.example.com/courses/12345")
        return


    output_path = args.output or str(args.assignment)  # Default output directory

    try:
        download_submissions(api_key, base_url, course_id, args.assignment, output_path, args.convert)
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()