REGISTRY=gcr.io/etcd-development/etcd

# For each machine
ETCD_VERSION=v3.6.0
TOKEN=my-etcd-token
CLUSTER_STATE=new
NAME_1=etcd-node-0
NAME_2=etcd-node-1
NAME_3=etcd-node-2
HOST_1=172.17.0.1
HOST_2=172.17.0.1
HOST_3=172.17.0.1
CLUSTER=${NAME_1}=http://${HOST_1}:2380,${NAME_2}=http://${HOST_2}:2382,${NAME_3}=http://${HOST_3}:2384
DATA_DIR=/var/lib/etcd

# For node 1
THIS_NAME=${NAME_1}
THIS_IP=${HOST_1}
THIS_CLIENT_PORT=2379
#THIS_CLIENT_PORT=2381
#THIS_CLIENT_PORT=2383
THIS_PEER_PORT=2380
#THIS_PEER_PORT=2382
#THIS_PEER_PORT=2384
docker volume create --name etcd-data-${THIS_NAME}

docker run -p ${THIS_CLIENT_PORT}:2379 -p ${THIS_PEER_PORT}:2380   --volume=etcd-data-${THIS_NAME}:/etcd-data   --name ${THIS_NAME} ${REGISTRY}:${ETCD_VERSION}   /usr/local/bin/etcd   --data-dir=/etcd-data --name ${THIS_NAME} --initial-advertise-peer-urls http://${THIS_IP}:${THIS_PEER_PORT} --listen-peer-urls http://0.0.0.0:2380   --advertise-client-urls http://${THIS_IP}:${THIS_CLIENT_PORT} --listen-client-urls http://0.0.0.0:2379   --initial-cluster ${CLUSTER}   --initial-cluster-state ${CLUSTER_STATE} --initial-cluster-token ${TOKEN}
