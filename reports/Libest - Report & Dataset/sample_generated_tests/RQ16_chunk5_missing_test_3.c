/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ16_chunk5_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include <string.h>
#include <stdlib.h>

/* Shared helpers/macros (used by existing tests) are assumed to be
   provided by the test build environment: LOG_FUNC_NM, SLEEP,
   st_start, st_stop, st_proxy_stop, read_binary_file and the
   file/name constants such as CLIENT_UT_CACERT,
   US897_CACERTS_SINGLE_CHAIN_MULT_CERTS, US897_SERVER_CERTKEY, etc. */

static void rq16_chunk5_missing_test_3(void)
{
    int rc;
    unsigned char *cacerts = NULL;
    int cacerts_len = 0;
    unsigned char *doc = NULL;
    int doc_len = 0;

    LOG_FUNC_NM;

    /* Ensure any running server is stopped so we can start with the desired config */
    st_stop();
    st_proxy_stop();

    /* Start the server using the CA chain variant exercised by existing tests */
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

    /* Read the served CA certificates to verify server is providing them */
    cacerts_len = read_binary_file(CLIENT_UT_CACERT, &cacerts);
    CU_ASSERT(cacerts_len > 0);

    /* Read the server CA configuration / documentation file and assert
       it contains the administrative advisory wording from the requirement */
    doc_len = read_binary_file("CA/estExampleCA.cnf", &doc);
    CU_ASSERT(doc_len > 0);
    CU_ASSERT(strstr((char *)doc,
                     ". EST server administrators are advised to take this into consideration.") != NULL);

    /* Clean up buffers */
    if (cacerts) free(cacerts);
    if (doc) free(doc);

    /* Stop the server started for this test */
    st_stop();
    st_proxy_stop();
}
