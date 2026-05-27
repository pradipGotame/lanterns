/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk11_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

void rq13_chunk11_missing_test_2(void)
{
    int rc;
    unsigned char *cacerts = NULL;
    int cacerts_len = 0;
    unsigned char *cacrlcerts = NULL;
    int cacrlcerts_len = 0;
    EST_CTX *ectx = NULL;
    int rv;

    /*
     * Start an EST server instance using a CA cert chain (multi-chain)
     */
    rc = st_start(US897_SERVER_PORT,
                  US897_SERVER_CERTKEY,
                  US897_SERVER_CERTKEY,
                  "RQ13 test realm",
                  US897_CACERTS_MULTI_CHAIN_CRLS,
                  US897_TRUST_CERTS,
                  "CA/estExampleCA.cnf",
                  0, 0, 0);
    CU_ASSERT(rc == 0);
    if (rc) return;
    SLEEP(1);

    /*
     * Read in the client trust store and create a client context
     */
    cacrlcerts_len = read_binary_file(CLIENT_UT_CACERT, &cacrlcerts);
    CU_ASSERT(cacrlcerts_len > 0);
    if (cacrlcerts_len <= 0) {
        return;
    }

    ectx = est_client_init(cacrlcerts, cacrlcerts_len, EST_CERT_FORMAT_PEM, client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);

    /*
     * Enable CRL checking on the client as in exemplars
     */
    rv = est_enable_crl(ectx);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Fetch the CA certificates from the server.  The presence of
     * subordinate CA certificates in this response supports the
     * requirement claim that subordinate certs are provided via
     * /cacerts rather than in the TLS Certificate message (which
     * therefore only needs to contain the server identity cert).
     */
    rv = est_client_get_cacerts(ectx, &cacerts, &cacerts_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    CU_ASSERT(cacerts_len > 0);

    /*
     * Cleanup
     */
    est_destroy(ectx);
    if (cacerts) free(cacerts);
    if (cacrlcerts) free(cacrlcerts);
}
