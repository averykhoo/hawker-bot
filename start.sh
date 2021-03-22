git pull

if [[ -e "stop.sh" ]]; then
    echo "./stop.sh exists"
    echo "please check if hawker-bot is running, and if not, manually remove ./stop.sh"
    ps -ef | grep "python hawker_bot.py"
    exit 0
fi

#TIMESTAMP=$(date "+%Y-%m-%d--%H-%M-%S")
#LOGDIR="./logs"
#mkdir -p $LOGDIR
#LOGFILE="$LOGDIR/hawker-bot--$TIMESTAMP.log"
#echo "to view stdout, tail $LOGFILE"

touch stop.sh
chmod +x stop.sh
echo "starting..."
#nohup python hawker_bot.py > $LOGFILE 2>&1 &
nohup python hawker_bot.py > /dev/null 2>&1 &
echo "kill -9 $!" > stop.sh
# shellcheck disable=SC2016
echo 'rm -- "$0"' >> stop.sh
echo "to stop: ./stop.sh"
