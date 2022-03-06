# Setting up minecraft on an EC2 instance

## Prerequisites
- Create your EC2 instance and select a valid keypair to SSH with

## Setting up
- SSH into your EC2 instance the run the following commands

```
sudo rpm --import https://yum.corretto.aws/corretto.key
sudo curl -L -o /etc/yum.repos.d/corretto.repo https://yum.corretto.aws/corretto.repo
```
These commands will import the corretto key and save the info for the corretto repo in the local yum repository.

After running these commands, we'll now install Java, git, and screen
```
sudo yum install -y java-17-amazon-corretto-devel
java -version
sudo yum install git
sudo yum install screen
```


Now we'll create the location we'll store minecraft servers in and also clone this repo into the ec2 instance
```
mkdir /opt/
mkdir /opt/minecraft
cd /opt/
git clone <THIS_REPO>
```


create a directory specifically with the name of the server you'd like to run (this can be anything that's a valid directory name)
```
mkdir /opt/minecraft/<SERVER_NAME>
cd /opt/minecraft/<SERVER_NAME>
```

now we download the server (1.18)
```
wget https://launcher.mojang.com/v1/objects/125e5adf40c659fd3bce3e66e67a16bb49ecc1b9/server.jar
mv server.jar minecraft_server.jar
```

### Running manually

```
java -Xmx1024M -Xms1024M -jar minecraft_server.jar nogui
```
Problem: you exit your ssh, this also exits.
This can be averted by using screen, but you still have to ssh in again to restart the server every time your ec2 instance restarts.


### Setting up run on start

```
cd /opt/<THIS_REPO>
mv minecraft-server/minecraft@.service /etc/systemd/system/minecraft@.service
./permission-set.sh
systemctl enable minecraft@<SERVER_NAME>
systemctl start minecraft@<SERVER_NAME>
```
**warning: by default, the jar that is run will be named minecraft_server.jar. If this is not the name of the jar you need to run for your server, create a server.conf file** 

#### Pros:
- whenever you restart your instance, the minecraft server also automatically restarts
- allows for configurations-per-server (read the .service file)
- allows for multiple servers to be run easily
- integrates very well with the next part

#### Cons:
- more configuration to get started


## Setting server lifecycle based on user count
Turns out that running a minecraft server can rack up a good amount of costs even with no users online.
In order to reduce the amount we pay, we can detect when the server is good to shut off and then make a user's request trigger the server startup. This adds a *slight* amount of downtime for a user, but saves a tremendous amount of money with larger servers/ mods.
### Step 0: Add a tag to existing EC2 instance
service = minecraft

### Step 1: Emitting user-count metric
Create an IAM role for your EC2 instance with the following managed policy attached: `CloudWatchAgentServerPolicy`
```
mkdir /opt/minecraft/admin
mv /opt/<THIS_REPO>/minecraft-server/admin /opt/minecraft/admin
crontab -e * * * * * /opt/minecraft/admin/online_users.sh
```
now, every minute, your cron job will be outputting metrics to cloudwatch specifying how many users are online

### Step 2: Create a cloudwatch alarm
aws console -> cloudwatch -> all alarms -> create alarm -> select metric -> minecraft -> metrics with no dimensions -> current-users -> select metric -> statistic = `Maximum`, period= `5 minutes` lower/equal than 0 -> additional configuration -> `3 out of 3` -> next -> create new topic -> next -> create alarm

This will create an alert for whenever the server has 0 people online. This will be sent to an SNS topic, which will then send it out to its subscribers (which we will set up in the next step).


### Step 3: Create a lambda function
create a lambda function with python3 as its version
leave every other field as default
choose a name (e.g. `minecraft-server-maintenance`)
copy and paste code from `server-maintenance-lambda/handler.py` into the lambda function and deploy.

create a trigger for the lambda function and link it to the sns topic that was created with the cloudwatch alarm.

### Step 4: Create another lambda function
create a lambda function with python3 as its verion and `minecraft-server-start` as its name
copy and paste code from `server-start-lambda/handler.py` into the lambda function and deploy.


This function will start the ec2 server when it is invoked


### Step 5: Create a t2.nano ec2 instance
We're going to create a pilot-light server. This will have an http endpoint which users can use to start the server as they'd like (IP:8080/status).
when a request is detected, the server will invoke the start lambda. Players will then be able to access the real server within 2-3 minutes (perhaps longer with bigger mods)


repeat all prerequisites for the original server up to & including `git clone <THIS_REPO>`

```
cd /opt/<THIS_REPO>
mv standby-server/pilot-server.py /opt/minecraft/pilot-server.py
mv standby-server/pilot-server.service /etc/systemd/system/pilot-server.service
./permission-set.sh
systemctl enable pilot-server
systemctl start pilot-server
```

### Step 6: IAM permissions
create an IAM policy that allows your t2.nano ec2 instance to perform `lambda:InvokeFunction` on `minecraft-server-start`
attach this policy to a role you create for your t2.nano server and attach the role to the ec2 instance.

### Step 7: IAM permissions (part 2)
create an IAM policy that allows the following api calls against your minecraft server's ec2 instance
```
	"ec2:StartInstances",
    "ec2:DescribeInstances",
    "ec2:DescribeInstanceStatus"
```
attach this policy to role used by `minecraft-server-start`

create an IAM policy that allows the following api calls against your minecraft server's ec2 instance
```
	"ec2:StopInstances",
	"ec2:DescribeInstances",
	"ec2:DescribeInstanceStatus"
```
attach this policy to the role used by lambda that stops the server.

### Step 7: Attach Elastic IPs to each EC2 instance
These IPs will be helpful when it comes to stuff related to route 53 and failover.

### Step 8: Add a health check to the minecraft server's EC2 instance.
healthcheck.py exists in the admin folder for a reason!
this will be used to configure failover on the DNS
```
cd /opt/<THIS_REPO>
mv minecraft-server/minecraft-health.service /etc/systemd/system/minecraft-health.service
systemctl enable minecraft-health
systemctl start minecraft-health
```

### Step 9: Buy a domain name on route 53 (if you don't have one)
This domain name will be the front-facing info the users can see.
We'll be setting up a failover configuration for a subdomain in the hosted zone created by this

### Step 10: Configure a health check for your minecraft server.
http://<ELASTIC_IP>:8080/health

### Step 11: Configure two A records in the hosted zone for your domain name
Same Record name & Failover routing policy for both.
Primary failover is the elastic ip for the minecraft server. Attach the health check from step 10 to this record. Record ID can be whatever you want.
Secondary failover is the elastic ip for the pilot-server. Record ID can be whatever you want.



## Summary of server lifecycle

- Server functions normally when users are on it
- Once 15 minutes have passed with no users online for more than a minute, an alarm triggers, which subsequently causes the EC2 instance hosting the server to stop
- This causes the health check for the instance to fail, thus redirecting requests to the domain name to the pilot-server instance.
- When a user tries to connect to the server using the domain name and the server is offline, nothing will occur. If users want to start the server, they can hit the endpoint configured in the pilot server

### Stopping flow
1. cloudwatch alarm triggers
2. sns topic receives alarm message
3. lambda function receives sns message
4. lambda function stops minecraft server
5. route 53 health check fails, causing failover to pilot-server server

### Starting flow
1. pilot-server server receives http request from user wishing to play minecraft
2. pilot-server server invokes lambda function
3. lambda function starts ec2 server
4. user receives 'out of bounds' error 
5. server is fully started
6. user reattempts connecting to server and succeeds

### How to access the server as a User

Assume server dns name is `DNS`:
1. User hits DNS:8080/status from their web browser
2. User receives status from server
3. If status is `starting`, user waits 3 minutes and then checks the status again
4. Until the status says `started`, user will repeat step 3, unless more than 10 minutes have passed (at which point it is save to assume a critical error has occured)
5. Once the user receives a `started` status, the user is able to connect to the minecraft server- if the user is not able to connect to the server, but the status says `started`, it is likely the case that the server itself is still starting. Wait up to 5 minutes for the server to come online - some modpacks take a while to initialize.