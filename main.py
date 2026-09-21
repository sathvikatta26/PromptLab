from flask import Flask, jsonify, request, render_template
from transformers import pipeline
import sqlite3
import os
import re

app = Flask(__name__)

# ============================================================
# DATABASE CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "database",
    "promptlab.db"
)


# ============================================================
# DATABASE SETUP
# ============================================================

def init_db():

    os.makedirs(
        os.path.dirname(DATABASE),
        exist_ok=True
    )

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            prompt TEXT NOT NULL,

            response TEXT,

            temperature REAL DEFAULT 0.7,

            max_tokens INTEGER DEFAULT 50,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    connection.commit()

    connection.close()


# Initialize database
init_db()


# ============================================================
# LOAD LOCAL GPT-2
# ============================================================

print("Loading local GPT-2 model...")

generator = pipeline(
    "text-generation",
    model="gpt2"
)

print("GPT-2 model loaded successfully.")


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# PROMPT ANALYSIS API
# ============================================================

@app.route(
    "/api/test",
    methods=["POST"]
)
def test_prompt():

    data = request.get_json(
        silent=True
    ) or {}

    prompt = str(
        data.get("prompt", "")
    ).strip()

    if not prompt:

        return jsonify({
            "error": "Prompt is required"
        }), 400


    # Word count
    words = len(
        re.findall(
            r"\S+",
            prompt
        )
    )


    # Character count
    characters = len(prompt)


    return jsonify({

        "prompt": prompt,

        "words": words,

        "characters": characters,

        "status":
            "Prompt tested successfully"

    })


# ============================================================
# GPT-2 GENERATION API
# ============================================================

@app.route(
    "/api/generate",
    methods=["POST"]
)
def generate_text():

    data = request.get_json(
        silent=True
    ) or {}


    prompt = str(
        data.get("prompt", "")
    ).strip()


    if not prompt:

        return jsonify({
            "error": "Prompt is required"
        }), 400


    # Get temperature
    try:

        temperature = float(
            data.get(
                "temperature",
                0.7
            )
        )

    except (ValueError, TypeError):

        temperature = 0.7


    # Get max tokens
    try:

        max_tokens = int(
            data.get(
                "max_tokens",
                50
            )
        )

    except (ValueError, TypeError):

        max_tokens = 50


    # Keep values within safe limits

    temperature = max(
        0.1,
        min(
            temperature,
            1.5
        )
    )


    max_tokens = max(
        10,
        min(
            max_tokens,
            200
        )
    )


    try:

        print(
            f"Generating text | "
            f"Temperature: {temperature} | "
            f"Max Tokens: {max_tokens}"
        )


        result = generator(

            prompt,

            max_new_tokens=max_tokens,

            temperature=temperature,

            do_sample=True,

            num_return_sequences=1

        )


        generated_text = result[0][
            "generated_text"
        ]


        return jsonify({

            "prompt": prompt,

            "response": generated_text,

            "temperature": temperature,

            "max_tokens": max_tokens

        })


    except Exception as error:

        print(
            "Generation error:",
            error
        )

        return jsonify({

            "error":
                "GPT-2 generation failed: "
                + str(error)

        }), 500


# ============================================================
# SAVE PROMPT API
# ============================================================

@app.route(
    "/api/save",
    methods=["POST"]
)
def save_prompt():

    data = request.get_json(
        silent=True
    ) or {}


    prompt = str(
        data.get("prompt", "")
    ).strip()


    response = str(
        data.get("response", "")
    )


    if not prompt:

        return jsonify({

            "error":
                "Prompt is required"

        }), 400


    # Temperature
    try:

        temperature = float(
            data.get(
                "temperature",
                0.7
            )
        )

    except (ValueError, TypeError):

        temperature = 0.7


    # Max tokens
    try:

        max_tokens = int(
            data.get(
                "max_tokens",
                50
            )
        )

    except (ValueError, TypeError):

        max_tokens = 50


    temperature = max(
        0.1,
        min(
            temperature,
            1.5
        )
    )


    max_tokens = max(
        10,
        min(
            max_tokens,
            200
        )
    )


    try:

        connection = sqlite3.connect(
            DATABASE
        )

        cursor = connection.cursor()


        cursor.execute("""
            INSERT INTO prompts
            (
                prompt,
                response,
                temperature,
                max_tokens
            )
            VALUES (?, ?, ?, ?)
        """, (

            prompt,

            response,

            temperature,

            max_tokens

        ))


        connection.commit()

        new_id = cursor.lastrowid

        connection.close()


        return jsonify({

            "status":
                "Prompt saved successfully",

            "id":
                new_id

        })


    except Exception as error:

        print(
            "Database save error:",
            error
        )

        return jsonify({

            "error":
                "Could not save prompt: "
                + str(error)

        }), 500


# ============================================================
# PROMPT HISTORY API
# ============================================================

@app.route(
    "/api/history",
    methods=["GET"]
)
def prompt_history():

    try:

        connection = sqlite3.connect(
            DATABASE
        )

        connection.row_factory = (
            sqlite3.Row
        )

        cursor = connection.cursor()


        cursor.execute("""
            SELECT
                id,
                prompt,
                response,
                temperature,
                max_tokens,
                created_at
            FROM prompts
            ORDER BY id DESC
        """)


        rows = cursor.fetchall()

        connection.close()


        history = []


        for row in rows:

            history.append({

                "id":
                    row["id"],

                "prompt":
                    row["prompt"],

                "response":
                    row["response"] or "",

                "temperature":
                    row["temperature"],

                "max_tokens":
                    row["max_tokens"],

                "created_at":
                    row["created_at"]

            })


        return jsonify(
            history
        )


    except Exception as error:

        print(
            "History error:",
            error
        )

        return jsonify({

            "error":
                "Could not load history: "
                + str(error)

        }), 500


# ============================================================
# DASHBOARD API
# ============================================================

@app.route(
    "/api/dashboard",
    methods=["GET"]
)
def dashboard():

    try:

        connection = sqlite3.connect(
            DATABASE
        )

        connection.row_factory = (
            sqlite3.Row
        )

        cursor = connection.cursor()


        # ----------------------------------------------------
        # Total prompts
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total_prompts
            FROM prompts
        """)

        total_prompts = cursor.fetchone()[
            "total_prompts"
        ]


        # ----------------------------------------------------
        # Average temperature
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                COALESCE(
                    AVG(temperature),
                    0
                ) AS avg_temperature
            FROM prompts
        """)

        avg_temperature = cursor.fetchone()[
            "avg_temperature"
        ]


        # ----------------------------------------------------
        # Total words
        # ----------------------------------------------------

        cursor.execute("""
            SELECT prompt
            FROM prompts
        """)

        prompt_rows = cursor.fetchall()


        total_words = 0

        total_characters = 0


        for row in prompt_rows:

            prompt_text = row[
                "prompt"
            ] or ""


            total_words += len(
                re.findall(
                    r"\S+",
                    prompt_text
                )
            )


            total_characters += len(
                prompt_text
            )


        # ----------------------------------------------------
        # Latest prompt
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                prompt,
                response,
                temperature,
                max_tokens,
                created_at
            FROM prompts
            ORDER BY id DESC
            LIMIT 1
        """)


        latest_row = cursor.fetchone()


        latest = None


        if latest_row:

            latest = {

                "id":
                    latest_row["id"],

                "prompt":
                    latest_row["prompt"],

                "response":
                    latest_row["response"] or "",

                "temperature":
                    latest_row["temperature"],

                "max_tokens":
                    latest_row["max_tokens"],

                "created_at":
                    latest_row["created_at"]

            }


        connection.close()


        return jsonify({

            "total_prompts":
                total_prompts,

            "avg_temperature":
                round(
                    float(
                        avg_temperature
                    ),
                    2
                ),

            "total_words":
                total_words,

            "total_characters":
                total_characters,

            "latest":
                latest

        })


    except Exception as error:

        print(
            "Dashboard error:",
            error
        )

        return jsonify({

            "error":
                "Could not load dashboard: "
                + str(error)

        }), 500


# ============================================================
# DELETE PROMPT API
# ============================================================

@app.route(
    "/api/delete/<int:prompt_id>",
    methods=["DELETE"]
)
def delete_prompt(prompt_id):

    try:

        connection = sqlite3.connect(
            DATABASE
        )

        cursor = connection.cursor()


        cursor.execute("""
            DELETE FROM prompts
            WHERE id = ?
        """, (
            prompt_id,
        ))


        connection.commit()


        deleted = cursor.rowcount


        connection.close()


        if deleted == 0:

            return jsonify({

                "error":
                    "Prompt not found"

            }), 404


        return jsonify({

            "status":
                "Prompt deleted successfully"

        })


    except Exception as error:

        print(
            "Delete error:",
            error
        )

        return jsonify({

            "error":
                "Could not delete prompt: "
                + str(error)

        }), 500


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )