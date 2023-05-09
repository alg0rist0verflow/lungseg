FROM python:3.7.16-slim-buster
ADD requirements.txt .
ADD segment.py .
ADD data/ .
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT ["python","segment.py"]