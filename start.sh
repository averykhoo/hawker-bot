git pull

mkdir -p logs
DATE=$(date "+%Y-%m-%d--%H-%M-%S")
echo "to view stdout, tail ./logs/$DATE.log"

echo "starting..."
python hawker_bot.py &> "logs/$DATE.log"
echo "stopped"
