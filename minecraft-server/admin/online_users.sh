total_conn_ct=$(netstat -an | grep 25565 | wc -l);
default_conn_ct=1
zero=0
total_conn_ct=$(( total_conn_ct - default_conn_ct))
total_conn_ct=$(( total_conn_ct >= zero  ? total_conn_ct : zero ))
aws cloudwatch put-metric-data   --namespace "minecraft"   --metric-name "current-users" --value $total_conn_ct