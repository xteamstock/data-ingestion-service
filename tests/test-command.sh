curl -X POST "https://data-ingestion-service-ud5pi5bwfq-as.a.run.app/api/v1/crawl/trigger" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "gd_lkaxegm826bjpoo9m5",
    "platform": "facebook", 
    "competitor": "nutifood",
    "brand": "growplus-nutifood",
    "category": "sua-bot-tre-em",
    "url": "https://www.facebook.com/GrowPLUScuaNutiFood/?locale=vi_VN",
    "num_of_posts": 3,
    "start_date": "2024-01-01",
    "end_date": "2024-01-01",
    "include_profile_data": true
  }'