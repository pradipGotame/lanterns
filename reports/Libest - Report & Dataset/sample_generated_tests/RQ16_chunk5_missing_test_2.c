/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ16_chunk5_missing_test_2.c
 */

static void rq16_chunk5_missing_test_2 (void)
{
    int rc;
    unsigned char *cacerts = NULL;
    int cacerts_len = 0;

    LOG_FUNC_NM;

    /*
     * Stop any existing server instance so we can start with the
     * CA chain that includes multiple intermediate certificates.
     */
    st_stop();

    /*
     * Start the EST server using a CA cert chain that contains multiple certs
     * (simulates configuration that may include unnecessary intermediates).
     */
    rc = st_start(US897_SERVER_PORT,
                  US897_SERVER_CERTKEY,
                  US897_SERVER_CERTKEY,
                  "RQ16 chunk5 test realm",
                  US897_CACERTS_SINGLE_CHAIN_MULT_CERTS,
                  US897_TRUST_CERTS,
                  "CA/estExampleCA.cnf",
                  0, 0, 0);
    CU_ASSERT(rc == 0);
    if (rc) return;
    SLEEP(1);

    /*
     * Read the server's served CA certificates and assert they are present.
     * This verifies the server surface administrators must be advised about.
     */
    cacerts_len = read_binary_file(CLIENT_UT_CACERT, &cacerts);
    CU_ASSERT(cacerts_len > 0);

    /*
     * Clean up
     */
    if (cacerts) free(cacerts);
    st_stop();
}
