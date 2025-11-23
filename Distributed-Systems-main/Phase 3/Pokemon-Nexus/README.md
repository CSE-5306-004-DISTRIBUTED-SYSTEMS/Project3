# Pokemon Nexus

## Install Dependencies on Debian-based Linux distribution like Ubuntu
```bash
sudo apt update
sudo apt install python3 python3-pip
pip3 install pandas matplotlib
```

## Part 1: Running and Testing Layered Architecture

### Step 1: 
Bring up application stack for Layered Architecture and access it through the web
```bash
docker compose -f ./layered/docker-compose.yaml up --build -d
http://localhost:5000/ 
```

### Step 2: 
Run a load test for this running Layered Architecture (5 mins duration)
```bash
docker compose -f ./load_test/layered/docker-compose.yaml up --build -d
```

### Step 3: 
Remove the test containers
```bash
docker compose -f ./load_test/layered/docker-compose.yaml down --volumes
```

### Step 4: 
Generate the graphs from test result data generated from Step 3
```bash
cd ./load_test/layered && python3 ./analyze_results.py
```
Note: As per the terminal message, "Analysis Complete! Graphs are saved in the 'test_results/analysis' directory."

### Step 5: 
Tear down the application stack of Layered Architecture.
(First, we need to go back to root directory and then return to the Layered Architecture source code)
```bash
cd ../..
docker compose -f ./layered/docker-compose.yaml down --volumes
```



## Part 2: Running and Testing Microservices Architecture

### Step 1: 
Bring up application stack for Microservices Architecture and access it
```bash
docker compose -f ./microservices/docker-compose.yaml up --build -d
http://localhost:8080/
```

### Step 2: 
Run a load test for this running Microservices Architecture (5 mins duration)
```bash
docker compose -f ./load_test/microservices/docker-compose.yaml up --build -d
```

### Step 3: 
Remove the test containers 
```bash
docker compose -f ./load_test/microservices/docker-compose.yaml down --volumes
```

### Step 4: 
Generate the graphs from test result data generate from Step 3
```bash
cd ./load_test/microservices && python3 ./analyze_results.py
```
Note: As per the terminal message, "Analysis Complete! Graphs are saved in the 'test_results/analysis' directory."

### Step 5: 
Tear down the application stack of Microservices Architecture.
(First, we need to go back to root directory and then return to the Layered Architecture source code)
```bash
cd ../..
docker compose -f ./microservices/docker-compose.yaml down --volumes
```