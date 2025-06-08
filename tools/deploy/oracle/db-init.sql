alter session set CONTAINER = freepdb1;

grant connect, resource to app;

grant select on v_$transaction to app;
