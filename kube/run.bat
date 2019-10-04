REM __create secret with configuration__  
kubectl create secret -n operational-inteligence generic config-elc --from-file=conf=secrets/config.ini

REM __deploy service and ingress__  
kubectl create -f service.yaml

REM __deploy the frontend__  
kubectl create -f deployment.yaml