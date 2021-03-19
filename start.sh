git pull

mkdir -p logs
DATE=$(date "+%Y-%m-%d--%H-%M-%S")
echo "to view stdout, tail ./logs/$DATE.log"

echo "starting..."
nohup python hawker_bot.py > "logs/$DATE.log" 2>&1 &
echo $! > nohup_pid.txt

echo "to stop: kill -9 $(cat nohup_pid.txt)"
