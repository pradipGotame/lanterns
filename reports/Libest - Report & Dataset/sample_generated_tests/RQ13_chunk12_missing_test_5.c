/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk12_missing_test_5.c
 */

void rq13_chunk12_missing_test_5(void)
{
    EST_CTX *ectx = NULL;
    int rc, rv;
    unsigned char *cacerts = NULL;
    int cacerts_len = 0;
    int pkcs7_len = 0;
    EVP_PKEY *key = NULL;

    /*
     * Start the EST server using a CA chain that contains
     * only the explicit trust anchor (no implicit TA certs).
     * This exercises the server's Explicit TA database usage.
     */
    rc = st_start(US897_SERVER_PORT,
                  US897_SERVER_CERTKEY,
                  US897_SERVER_CERTKEY,
                  "RQ13 test realm",
                  US897_CACERTS_SINGLE_CHAIN_MULT_CERTS,
                  US897_TRUST_CERTS,
                  "CA/estExampleCA.cnf",
                  0, 0, 0);
    CU_ASSERT(rc == 0);
    if (rc) return;
    SLEEP(1);

    /*
     * Read in the client-side CA certs (explicit TA) and create a client
     * context that will validate server certs against the explicit TA DB.
     */
    cacerts_len = read_binary_file(CLIENT_UT_CACERT, &cacerts);
    CU_ASSERT(cacerts_len > 0);
    if (cacerts_len <= 0) {
        return;
    }

    ectx = est_client_init(cacerts, cacerts_len,
                           EST_CERT_FORMAT_PEM,
                           client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);
    if (!ectx) return;

    /*
     * Attempt to re-enroll using a client cert that chains to the EST CA.
     * Success here demonstrates the server authenticated the client
     * using the Explicit TA database supplied at startup.
     */
    rv = est_client_reenroll(ectx, cert, &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    est_destroy(ectx);
}
