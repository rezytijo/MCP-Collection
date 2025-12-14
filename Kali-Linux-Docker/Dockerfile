# Use Kali Linux as base for security tools
FROM kalilinux/kali-rolling

# Set working directory
WORKDIR /app

# Set Python unbuffered mode
ENV PYTHONUNBUFFERED=1

# Update and install required tools and Python
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    nmap \
    nikto \
    sqlmap \
    wpscan \
    dirb \
    exploitdb \
    dnsutils \
    whois \
    curl \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Copy the server code
COPY pentest_server.py .

# # Create non-root user
# RUN useradd -m -u 1000 mcpuser && \
#     chown -R mcpuser:mcpuser /app && \
#     # Grant capabilities for network tools
#     setcap cap_net_raw,cap_net_admin,cap_net_bind_service+eip /usr/bin/nmap

# # Switch to non-root user
# USER mcpuser

# Run the server
CMD ["python3", "pentest_server.py"]