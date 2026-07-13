FROM 415424935168.dkr.ecr.us-east-1.amazonaws.com/pax8-python-base:3.12-latest AS builder

# Create non-root user/group in builder stage
RUN addgroup -g 2000 appgroup && \
    adduser -u 1000 -G appgroup -s /bin/sh -D app

# Set environment variables
ENV APP_DIR=/app
ENV VENV_DIR=/usr/local/venv
ENV PATH="$VENV_DIR/bin:${PATH}"
ENV HOME=/home/app
ENV PYTHONPATH="$APP_DIR"

# Install system dependencies as root
RUN apk add --no-cache \
    py3.12-pip \
    ; \
    # Create app directory and set permissions
    mkdir -p $APP_DIR && \
    chown -R app:appgroup $APP_DIR && \
    # Create venv directory with correct permissions
    mkdir -p $VENV_DIR && \
    chown -R app:appgroup $VENV_DIR

# Switch to non-root user
USER app

WORKDIR $APP_DIR

# Copy requirements with correct ownership
COPY --chown=app:appgroup requirements.txt .

# Create and activate virtual environment as non-root user
RUN python -m venv $VENV_DIR && \
    $VENV_DIR/bin/pip install --no-cache-dir -r requirements.txt

FROM 415424935168.dkr.ecr.us-east-1.amazonaws.com/pax8-python-base:3.12-latest

# Create same user/group in final stage
RUN addgroup -g 2000 appgroup && \
    adduser -u 1000 -G appgroup -s /bin/sh -D app

# Set environment variables
ENV APP_DIR=/app
ENV VENV_DIR=/usr/local/venv
ENV PATH="$VENV_DIR/bin:${PATH}"
ENV HOME=/home/app
ENV PYTHONPATH="$APP_DIR"
ENV STREAMLIT_SERVER_MAX_MESSAGE_SIZE=300

# Create directories and set permissions
RUN mkdir -p $APP_DIR $VENV_DIR && \
    chown -R app:appgroup $APP_DIR $VENV_DIR

# Switch to non-root user
USER app

WORKDIR $APP_DIR

# Copy virtual environment and app files with correct ownership
COPY --from=builder --chown=app:appgroup $VENV_DIR $VENV_DIR
COPY --chown=app:appgroup . $APP_DIR

EXPOSE 8501

CMD ["streamlit", "run", "src/app.py"]
