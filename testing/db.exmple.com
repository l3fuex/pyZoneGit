; supported format
$ORIGIN example.com.
$TTL 86400
@   IN  SOA ns1.example.com. admin.example.com. (
            2024071501 ; Serial
            3600       ; Refresh
            1800       ; Retry
            1209600    ; Expire
            86400 )    ; Minimum TTL

    IN  NS      ns1.example.com.
    IN  NS      ns2.example.com.

    IN  MX  10  mail

ns1 IN  A       192.0.2.1
ns2 IN  A       192.0.2.2
www IN  A       192.0.2.3
