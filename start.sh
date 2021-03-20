git pull

mkdir -p logs
DATE=$(date "+%Y-%m-%d--%H-%M-%S")
echo "to view stdout, tail ./logs/$DATE.log"

echo "kill -9 " > stop.sh
chmod +x stop.sh
echo "starting..."
nohup python hawker_bot.py > "logs/$DATE.log" 2>&1 &
echo $! >> stop.sh

echo "to stop: ./stop.sh"
echo "to stop: kill -9 $(cat nohup_pid.txt)"
