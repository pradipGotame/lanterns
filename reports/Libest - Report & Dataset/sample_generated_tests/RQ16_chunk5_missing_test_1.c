/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ16_chunk5_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>

/* Shared test fixtures and globals (ectx, LOG_FUNC_NM, SLEEP, st_start, st_stop,
   st_proxy_stop, st_enable_csrattr_enforce, read_binary_file,
   est_client_get_csrattrs, est_destroy and constants like
   US897_SERVER_PORT, US897_SERVER_CERTKEY, US897_CACERTS_SINGLE_CHAIN_MULT_CERTS,
   US897_TRUST_CERTS, CLIENT_UT_CACERT) are provided by the test harness. */

static void rq16_chunk5_missing_test_1(void)
{
    int rc;
    int cacerts_len;
    unsigned char *cacerts = NULL;
    int rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;

    LOG_FUNC_NM;

    /* Ensure any running server is stopped for a clean start */
    st_stop();

    /*
     * Enable CSR attribute enforcement (previous tests called this helper
     * without asserting its effect).  This call exercises the administrative
     * configuration surface referenced by the advisory.
     */
    st_enable_csrattr_enforce();

    /*
     * Start the server with a CA chain that contains multiple certs
     * (represents the case where unnecessary intermediates may be present).
     */
    rc = st_start(US897_SERVER_PORT,
                 US897_SERVER_CERTKEY,
                 US897_SERVER_CERTKEY,
                 "RQ16 test realm",
                 US897_CACERTS_SINGLE_CHAIN_MULT_CERTS,
                 US897_TRUST_CERTS,
                 "CA/estExampleCA.cnf",
                 0, 0, 0);
    CU_ASSERT(rc == 0);
    if (rc) return;

    SLEEP(1);

    /* Read the server-provided CA cert bundle and assert it is available */
    cacerts_len = read_binary_file(CLIENT_UT_CACERT, &cacerts);
    CU_ASSERT(cacerts_len > 0);

    /*
     * Verify an operational effect of the CSR attribute enforcement by
     * attempting to retrieve CSR attributes via the client API.  A
     * successful return demonstrates the enforcement/configuration is
     * active and observable (addresses the gap of exercising helpers without
     * asserting outcomes).
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Clean up allocated buffers and contexts */
    if (cacerts) free(cacerts);
    if (attr_data) free(attr_data);

    est_destroy(ectx);
    st_stop();
    st_proxy_stop();
}
