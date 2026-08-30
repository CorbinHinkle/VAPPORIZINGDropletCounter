from flask import Flask, render_template, request, jsonify
import os
import tempfile

from core.droplet_image_processing import process_images


app = Flask(__name__)

# Upload limit: 100 MB
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    try:
        files = request.files.getlist("images")

        if not files:
            return jsonify({
                "success": False,
                "error": "No images were uploaded."
            }), 400

        # Create temporary directory for this analysis
        with tempfile.TemporaryDirectory() as temp_folder:

            for file in files:

                if file.filename == "":
                    continue

                filepath = os.path.join(
                    temp_folder,
                    file.filename
                )

                file.save(filepath)

            # Parameters from webpage
            micron_per_pixel = float(
                request.form.get("micron_per_pixel", 0.0925)
            )

            min_diam = float(
                request.form.get("min_diam", 2)
            )

            max_diam = float(
                request.form.get("max_diam", 20)
            )

            # Diagnostics directory
            diag_folder = os.path.join(
                temp_folder,
                "diagnostics"
            )

            os.makedirs(
                diag_folder,
                exist_ok=True
            )

            # Run your actual image-processing algorithm
            diameters, areas, avg_image, image_count = process_images(
                temp_folder,
                micron_per_pixel,
                min_diam,
                max_diam,
                diag_folder
            )

            # Return results to JavaScript
            if len(diameters) == 0:

                return jsonify({
                    "success": True,
                    "image_count": image_count,
                    "droplet_count": 0,
                    "message": "No droplets detected."
                })

            return jsonify({
                "success": True,
                "image_count": image_count,
                "droplet_count": len(diameters),
                "min_diameter": float(diameters.min()),
                "max_diameter": float(diameters.max()),
                "mean_diameter": float(diameters.mean())
            })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)