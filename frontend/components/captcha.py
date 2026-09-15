"""Reusable CAPTCHA component for authentication forms."""

import io
import random
import string
import time

import streamlit as st
from PIL import Image, ImageDraw, ImageFont


CAPTCHA_EXPIRY_SECONDS = 60
CAPTCHA_LENGTH = 6


def _generate_code() -> str:
    """Generate a random CAPTCHA code."""

    characters = string.ascii_uppercase + string.digits

    # Remove easily confused characters.
    characters = characters.replace("O", "")
    characters = characters.replace("0", "")
    characters = characters.replace("I", "")
    characters = characters.replace("1", "")

    return "".join(
        random.choices(
            characters,
            k=CAPTCHA_LENGTH,
        )
    )


def _captcha_image(code: str) -> bytes:
    """Create a CAPTCHA image with noise."""

    width = 260
    height = 80

    image = Image.new(
        "RGB",
        (width, height),
        "white",
    )

    draw = ImageDraw.Draw(image)

    # -----------------------------------------------------
    # Noise lines
    # -----------------------------------------------------

    for _ in range(8):
        draw.line(
            (
                random.randint(0, width),
                random.randint(0, height),
                random.randint(0, width),
                random.randint(0, height),
            ),
            fill=(
                random.randint(100, 200),
                random.randint(100, 200),
                random.randint(100, 200),
            ),
            width=1,
        )

    # -----------------------------------------------------
    # Noise dots
    # -----------------------------------------------------

    for _ in range(100):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)

        draw.point(
            (x, y),
            fill=(
                random.randint(80, 200),
                random.randint(80, 200),
                random.randint(80, 200),
            ),
        )

    # -----------------------------------------------------
    # CAPTCHA characters
    # -----------------------------------------------------

    font = ImageFont.load_default(size=32)

    start_x = 25

    for index, character in enumerate(code):
        x = start_x + (index * 36)
        y = random.randint(18, 32)

        draw.text(
            (x, y),
            character,
            font=font,
            fill=(
                random.randint(0, 80),
                random.randint(0, 80),
                random.randint(0, 80),
            ),
        )

    # -----------------------------------------------------
    # Convert to PNG
    # -----------------------------------------------------

    buffer = io.BytesIO()
    image.save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()


def _create_captcha(key: str) -> None:
    """Create and store a new CAPTCHA."""

    code = _generate_code()

    version_key = f"{key}_captcha_version"

    st.session_state[version_key] = (
        st.session_state.get(
            version_key,
            0,
        )
        + 1
    )

    st.session_state[
        f"{key}_captcha_code"
    ] = code

    st.session_state[
        f"{key}_captcha_created_at"
    ] = time.time()

    st.session_state[
        f"{key}_captcha_image"
    ] = _captcha_image(code)


def refresh_captcha(key: str) -> None:
    """Generate a new CAPTCHA."""

    _create_captcha(key)


def captcha(key: str) -> tuple[bool, bool]:
    """
    Display CAPTCHA and validate the entered value.

    Returns:
        captcha_valid
        captcha_expired
    """

    code_key = f"{key}_captcha_code"
    created_key = f"{key}_captcha_created_at"
    image_key = f"{key}_captcha_image"
    version_key = f"{key}_captcha_version"

    # -----------------------------------------------------
    # Create CAPTCHA on first load
    # -----------------------------------------------------

    if (
        code_key not in st.session_state
        or created_key not in st.session_state
        or image_key not in st.session_state
        or version_key not in st.session_state
    ):
        _create_captcha(key)

    code = st.session_state[code_key]
    created_at = st.session_state[created_key]
    image_bytes = st.session_state[image_key]
    version = st.session_state[version_key]

    # -----------------------------------------------------
    # Check expiry
    # -----------------------------------------------------

    elapsed = time.time() - created_at

    expired = (
        elapsed >= CAPTCHA_EXPIRY_SECONDS
    )

    # -----------------------------------------------------
    # Security verification heading
    # -----------------------------------------------------

    st.markdown(
        "**Security verification**"
    )

    st.caption(
        "Enter the characters shown below. "
        "The CAPTCHA expires after 1 minute."
    )

    # -----------------------------------------------------
    # CAPTCHA image
    # -----------------------------------------------------

    st.image(
        image_bytes,
        width=260,
    )

    # -----------------------------------------------------
    # Refresh button
    #
    # This is intentionally here so it appears:
    # IMAGE -> REFRESH -> INPUT
    # -----------------------------------------------------

    refresh_clicked = st.form_submit_button(
        "↻ Generate New Image"
    )

    # -----------------------------------------------------
    # CAPTCHA input
    # -----------------------------------------------------

    input_key = (
        f"{key}_captcha_input_{version}"
    )

    entered = st.text_input(
        "CAPTCHA",
        key=input_key,
        placeholder=(
            "Enter the characters shown above"
        ),
        label_visibility="collapsed",
    )

    # -----------------------------------------------------
    # Handle refresh
    # -----------------------------------------------------

    if refresh_clicked:
        refresh_captcha(key)
        st.rerun()

    # -----------------------------------------------------
    # Validate
    # -----------------------------------------------------

    valid = (
        not expired
        and entered.strip().upper()
        == code.upper()
    )

    return valid, expired