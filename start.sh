git pull

echo "starting..."
DATE=$(date "+%Y-%m-%d--%H-%M-%S")
python hawker_bot.py &> "$DATE.log"
echo "stopped"
